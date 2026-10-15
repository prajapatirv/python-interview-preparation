---
id: foundations-architecture
title: System design & design patterns: from the basics (drafted)
stack: java
skill: architecture
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] What are the fallacies of distributed computing in practice?
tags: distributed-systems, fallacies, timeouts, retries, idempotency, resilience, basics

**Start here: the concepts**
- **Distributed system:** several programs on different machines that cooperate over a network to do one job. Microservices calling each other over HTTP are an example. It exists because one machine cannot hold all the load or survive its own failure.
- **Fallacy:** a belief that sounds true but is false. In 1994 Peter Deutsch and colleagues at Sun listed seven false beliefs engineers make about networks, and James Gosling later added an eighth. Each one causes real outages when we design as if it were true.
- **Latency:** the time one request takes to travel and get a reply. **Bandwidth:** how much data the link can carry per second.
- **Timeout:** a limit on how long we wait before giving up on a call.
- **Retry:** sending the call again after a failure.
- **Idempotent:** doing it twice has the same effect as doing it once. "Set the status to PAID" is idempotent. "Add 100 to the balance" is not.
- **Backpressure:** a slow consumer signals "slow down" or rejects work, so a fast producer cannot flood it.
- **Observability:** logs, metrics and traces that let you see what happened across services.

**The live scenario**
An order service handles 100 requests/second and calls a payment service that normally answers in 100 ms. One evening the payment service slows to 5 seconds. The order service has no timeout, so each call holds a thread. By Little's Law (concurrent calls = rate × time), it needs about 500 threads (100 × 5), but the pool has 200. The pool fills and the order service stops responding, even to health checks. Users click "Pay" again, and the retries create duplicate charges because payment is not idempotent. One slow dependency took down two services and cost money.

**What the interviewer is really checking**
Whether you can turn the eight fallacies into concrete engineering habits instead of reciting the list. A fresher should show that every remote call can be slow, fail or arrive twice.

**How I answer it**
1. **The network is reliable (false).** Packets get lost and servers restart. So I treat every remote call as able to fail, and I set timeouts and handle errors.
2. **Latency is zero (false).** A network call is thousands of times slower than a local method call. So I avoid chatty designs with many small calls, and I set a timeout shorter than the user's patience.
3. **Bandwidth is infinite (false).** Links have limits. So I send only the fields needed, paginate, and compress large payloads.
4. **The network is secure (false).** Traffic can be sniffed or spoofed. So I use TLS, authenticate every service and validate inputs, even inside the company network.
5. **Topology doesn't change (false).** Servers are added, moved and replaced, and IPs change. So I use service names and discovery, never hard-coded IPs.
6. **There is one administrator (false).** Different teams, vendors and clouds own different parts. So I agree on contracts, version my APIs and expect others to change things without telling me.
7. **Transport cost is zero (false).** Serialising data costs CPU and time, and network traffic costs money. So I choose compact formats and avoid needless calls.
8. **The network is homogeneous (false).** Different hardware, operating systems, protocols and languages are involved. So I rely on standard formats such as JSON or Protobuf, not language-specific ones.
9. **Combined practical result:** timeouts, retries (with limits and backoff), idempotency, backpressure and observability on every remote call. Retries are only safe when the operation is idempotent, so I send a unique key:
```
POST /payments   Idempotency-Key: order-123
```
The server stores the key and returns the first result if the same key arrives again.

**Trade-offs and what can go wrong**
- Timeouts that are too short cause false failures. Timeouts that are too long exhaust threads.
- Retries without backoff and a maximum count multiply load on a struggling service (a "retry storm").
- Idempotency needs storage and design effort.
- Backpressure means some requests get rejected, which is better than a total crash.
- A common mistake is testing only on a fast local network, where these failures never show up.

**How I'd monitor it**
- p95/p99 latency and error rate per downstream service.
- Timeout count, retry count and thread-pool usage.
- Circuit-breaker state (a circuit breaker stops calling a failing service for a while).
- Duplicate-request counts for idempotency keys.
- A correlation ID in every log line, so a Splunk search follows one request across services.
- Alerts on rising p99 and on pool usage above about 80%.

**Follow-ups to expect**
- *Why not retry every failure?* -> Retrying non-idempotent calls can duplicate effects, and unlimited retries overload a sick service. Use limits, backoff and idempotency keys.
- *How do you pick a timeout?* -> Measure the downstream p99 and set slightly above it, within the caller's overall time budget.
- *Which fallacy hurts most?* -> "The network is reliable," because it leads to missing timeouts and error handling.

**60-second answer**
The fallacies of distributed computing are false beliefs about networks: that they are reliable, with zero latency, infinite bandwidth, secure, unchanging, run by one administrator, free to use and uniform. In reality, calls fail, are slow, get duplicated and change over time. In practice I put a timeout on every remote call, retry only with limits and backoff, and make operations idempotent so a retry cannot charge twice. I add backpressure so a slow service is not flooded, and I use TLS and service discovery instead of fixed IPs. I also add logs, metrics and trace IDs so I can see which call is slow. Without these, one slow dependency can exhaust threads and bring down the whole chain.

### Q2 [fresher] Explain CAP and PACELC in one minute.
tags: cap-theorem, pacelc, consistency, availability, network-partition, distributed-systems, basics

**Start here: the concepts**
- **Distributed system:** several machines (nodes) working together, often in different data centers, so one failure does not take everything down. It exists for scale and resilience.
- **Replica:** a copy of the same data on another node. Replicas keep data safe and spread read traffic, but they create the risk that copies disagree.
- **Network partition:** the network between nodes breaks, so the nodes are alive but cannot talk to each other. Each side may keep accepting writes without knowing what the other side did. Partitions happen in real networks, so you cannot design them away.
- **Consistency (the C in CAP):** every read sees the latest successful write, as if there were one copy of the data.
- **Availability (the A in CAP):** every request to a working node gets a real answer, not an error or a timeout, even if that answer may be out of date.
- **CAP theorem:** when a partition happens, you must choose between consistency and availability. Since partitions cannot be avoided, the real choice is C or A, not "pick any two of three".
- **CP vs AP:** CP means that during a partition you refuse or limit some requests to stay correct. AP means you keep serving, possibly with stale data, and reconcile later.
- **Latency:** how long a request takes to answer.
- **PACELC:** CAP only describes the rare partition case. PACELC reads: if there is a **P**artition, choose **A** or **C**; **E**lse (normal operation), choose **L**atency or **C**onsistency. Checking with other replicas gives fresher data but costs time.

**The live scenario**
A shop runs in two regions with one database replicated between them. The link breaks for 4 minutes (illustrative numbers). The **payments** service rejects about 2% of requests, the ones it cannot safely confirm, because double-spending is worse than a retry. That is a CP choice. The **profile and feed** pages keep working from the local replica, and some users see a 3-minute-old photo. That is an AP choice. On a normal day there is no partition, but the team still chooses. Reading from the local replica takes 2 ms and may be slightly stale. Reading from the primary in the other region takes about 80 ms and is fresh. That trade-off is the "Else" part of PACELC.

**What the interviewer is really checking**
Whether you understand that CAP is about behavior during a failure, that the choice is per use case, and that you know PACELC adds the everyday latency-versus-consistency trade-off.

**How I answer it**
1. **Define a partition first.** CAP only makes sense once you say that the network can split and nodes cannot coordinate.
2. **State the rule.** During a partition you choose C or A. You cannot have both, because a node cut off from the others either waits or refuses (consistent but unavailable) or answers with what it knows (available but maybe stale).
3. **Give both sides.** CP rejects or limits requests. AP serves possibly stale data.
4. **Add PACELC.** Say that partitions are rare, but the latency-versus-consistency choice applies on every request. A fresher read means asking more replicas or a distant primary, which is slower.
5. **Tie it to business impact.** Payments and balances lean CP, because a wrong answer costs money. Feeds and profiles lean AP, because a stale answer costs little and an error costs users.
6. **Say it is tunable.** Many databases let you choose per operation, for example Cassandra consistency levels or MongoDB write concern and read preference. So label the operation, not the whole system.

**Trade-offs and what can go wrong**
- CP: users see errors or timeouts during a partition, so you need clear retries and messages.
- AP: copies can diverge, so you need a conflict rule such as last-write-wins, and you must accept that it can lose an update.
- Common mistakes: saying "pick any two of three", treating a database as permanently CP or AP, and forgetting the normal-operation trade-off.
- Consistency in CAP is strict, "latest write seen by everyone", which is stronger than the "consistency" in ACID.

**How I'd monitor it**
- Replication lag between replicas, with an alert when it passes the tolerated staleness.
- Error and timeout rates and p99 latency per endpoint, split by read and write.
- Splunk searches for write-rejected, quorum-not-reached or timeout errors, grouped by region and service.
- Inter-region network health checks, so a partition is detected before users report it.
- Conflict or reconciliation counts in AP stores.

**Follow-ups to expect**
- *Why can't we just have all three of C, A and P?* -> Partitions happen in real networks, so P is forced. During one, a cut-off node must either refuse (losing A) or answer possibly stale (losing C).
- *Is a database either CP or AP?* -> Not strictly. Many are tunable per query, such as quorum reads and writes, so the choice depends on the operation.
- *What does PACELC add over CAP?* -> It covers normal operation. Even with no partition you trade latency for consistency, for example a fast local replica read versus a slower fresh read.

**60-second answer**
A network partition means nodes are alive but cannot talk to each other. CAP says that during one I must choose. A CP system rejects or limits requests to stay consistent. An AP system keeps serving, possibly with stale data. PACELC adds that when there is no partition, I still choose between latency and consistency, because asking more replicas for fresh data is slower. I choose per use case. Payments lean CP, because a wrong balance costs money. Feeds and profiles lean AP, because a slightly old page is better than an error. I would watch replication lag, error rates and p99 latency to see these choices at work.

### Q3 [mid] What consistency models should you know?
tags: consistency-models, linearizability, eventual-consistency, causal-consistency, distributed-systems, replication, basics

**Start here: the concepts**
- **Replica:** a copy of the same data on another server. We keep copies for availability and read speed. Copies can briefly disagree, which is why consistency models exist.
- **Consistency model:** a promise about what a reader may see after a write when data is copied across servers. A stronger promise is easier for developers but costs more latency and availability.
- **Strong (linearizable):** the system behaves as if there were one copy and every operation happened instantly at one point in time. Once a write completes, every later read, from anyone, sees it. This is the strongest promise and the slowest, because replicas must coordinate.
- **Sequential:** all clients see operations in one agreed order that respects each client's own order. That order need not match real clock time, so a read may be stale compared with the clock. It is weaker than linearizable.
- **Causal:** if event B was caused by A (a reply to a comment, say), everyone sees A before B. Unrelated events may appear in different orders for different people.
- **Read-your-writes:** after you write something, your own later reads see it. Other people may still see the old value for a while.
- **Monotonic reads:** once you have seen a value, you never later see an older one. This stops data "going back in time" when requests hit different replicas.
- **Eventual:** if writes stop, all replicas converge to the same value, with no promise about when. Reads in between may be stale.
- Read-your-writes and monotonic reads are *session guarantees*, meaning they apply per user session. They are not global orderings like the others.
- **Not the same as serializable.** Serializable is a transaction isolation level, not a replica-visibility model.

**The live scenario**
A profile service handles about 2,000 reads/s and 20 writes/s. Reads go to replicas, with replication lag around 200 ms. A user changes their display name, the page reloads, and the old name appears. This happens for roughly 3% of edits and creates support tickets. The same team's balance endpoint must never show an old balance, or a user could overspend. One model for everything was wrong in both directions. Making the whole system strongly consistent would add latency to all reads, and making it eventual would be unsafe for money.

**What the interviewer is really checking**
Whether you understand the spectrum, can explain each level in plain words, and choose per feature by business risk instead of defaulting to "strong everywhere".

**How I answer it**
1. **Order the models from strongest to weakest:** linearizable, sequential, causal, then the session guarantees (read-your-writes, monotonic reads), then eventual. The reason is that each step down gives up some guarantee in exchange for lower latency and higher availability.
2. **Ask what the user would notice if they saw stale data.** Stale is harmless for a like counter, annoying for a profile edit, and dangerous for a balance. The business impact decides the model.
3. **Pick the weakest model that is still correct.** Weaker models are cheaper and scale better, and reads can be served by any nearby replica.
4. **Map the examples.** Profile edits need read-your-writes: route the author's reads to the primary, or to a replica that has caught up, for a short window after their write. Account balance needs strong consistency: read from the primary, or use quorum reads and writes.
5. **Use causal for conversations and feeds,** where seeing a reply before the original message would confuse people.
6. **Make it configurable per operation where the database allows.** Cassandra has per-query consistency levels such as QUORUM, and MongoDB has read and write concerns such as majority. Couchbase has durability levels for writes.

**Trade-offs and what can go wrong**
- Strong consistency costs latency, because each write waits for replicas. It also reduces availability during network partitions.
- Eventual consistency is cheap but pushes complexity to developers, who must handle stale reads and conflicting writes.
- A common mistake is saying "strong" without saying which kind. Linearizable is not the same as serializable.
- Another is assuming a load balancer will keep a user on one replica. Without monotonic reads, a refresh can show older data than the previous page.
- Routing every read to the primary "just in case" removes the benefit of having replicas.

**How I'd monitor it**
- Replication lag per replica, with an alert when it exceeds the staleness budget, e.g. 500 ms.
- Application-level stale-read checks: log the version returned and the version the user just wrote, and search for mismatches in Splunk.
- Support-ticket counts for "my change didn't save".
- p99 latency of strong reads versus replica reads, to confirm the cost is acceptable.

**Follow-ups to expect**
- *How do you implement read-your-writes?* -> Read from the primary for a few seconds after a user's write, or pass a version or timestamp token and read only from replicas that have reached it.
- *Linearizable versus serializable?* -> Linearizable concerns the order in which single-object operations become visible. Serializable concerns whether concurrent transactions behave as if run one at a time.
- *How does this relate to CAP?* -> During a network partition you choose between consistency and availability. Even without partitions you still trade latency against consistency (PACELC).

**60-second answer**
Consistency models are promises about what you can read after a write when data is copied across servers. From strongest to weakest: linearizable, where the system behaves like one copy; sequential, where everyone sees one agreed order; causal, where cause comes before effect; the session guarantees read-your-writes and monotonic reads; and finally eventual, where copies converge at some point. Stronger models are easier to reason about but cost latency and availability. So I pick the weakest model that is still correct for the feature. A profile edit needs read-your-writes, so the user sees their own change. An account balance needs strong consistency, because stale data could cause overspending. I watch replication lag and stale-read mismatches to check that the choice holds in production.

### Q4 [mid] How do you scale a stateless service and a database?
tags: scalability, stateless-service, load-balancer, read-replicas, caching, sharding, basics

**Start here: the concepts**
- **Stateless service:** a service that keeps nothing between requests in its own memory or disk. Any request can go to any copy, because all needed data comes from the request or from a shared store (database, cache). This is what makes copies interchangeable.
- **Horizontal vs vertical scaling:** horizontal means adding more machines or copies. Vertical means making one machine bigger (more CPU, RAM). Vertical is simple but has a ceiling and a single point of failure.
- **Load balancer:** a component that spreads incoming requests across the copies and stops sending traffic to unhealthy ones.
- **Autoscaling:** rules that add or remove copies automatically based on load (for example CPU or requests per instance).
- **Shared cache:** a fast in-memory store (such as Redis) used by all copies. It holds hot data and things like sessions, so no copy needs local state. It exists because memory is far faster than a database.
- **Read replica:** a copy of the database that receives changes from the main one (the primary) and serves only reads. It adds read capacity but not write capacity.
- **Replication lag:** the delay before a change on the primary shows up on a replica.
- **Partitioning/sharding:** splitting data across several databases by a key (such as customer ID), so each holds part of it and takes part of the writes.
- **CQRS:** Command Query Responsibility Segregation. Writes go to one model or store, and reads are served from a separate store shaped for queries.

**The live scenario**
A shopping site normally gets 500 requests/second. A flash sale pushes it to 3,000. The service is stateless, so autoscaling goes from 4 to 20 instances within minutes. But p99 latency still climbs from 200 ms to 6 s. The database CPU is at 95%, and 20 instances × 20 pooled connections = 400 connections against a database limit of 200, so requests queue for a connection. The service scaled easily and the database was the real bottleneck.

**What the interviewer is really checking**
Whether you know the app tier scales by copying, while the database holds the state and needs a deliberate, step-by-step strategy. Also whether you measure before changing anything.

**How I answer it**
1. **Make the service stateless first.** Move sessions and shared data to a cache or database. Then any instance can serve any request, and instances can be added or killed freely.
2. **Put copies behind a load balancer with health checks and autoscaling.** Size by Little's Law (concurrent requests = rate × time per request). At 2,000 req/s × 0.1 s = 200 in flight. If one instance handles about 50, you need 4, plus headroom, so about 6.
3. **Measure to find the real bottleneck.** Look at slow queries, CPU, connections and lock waits. Do not guess.
4. **Fix the database cheaply first.** Add indexes, fix bad queries, and tune connection pools. Scale vertically if that is the quick win.
5. **Add caching for hot, repeated reads.** It is often the cheapest way to remove load, and it protects the database.
6. **Add read replicas for read-heavy load.** Route reads there and writes to the primary.
7. **Shard when writes or data size exceed one primary.** Replicas cannot help here, because every write still hits the primary. Choose a key that spreads load evenly.
8. **Consider CQRS or separate stores** (for example a search index for queries) when read and write needs differ sharply.

The stored order is a common pattern, not a fixed law. Caching and query fixes usually come before replicas, and you always take the step that removes the measured bottleneck.

**Trade-offs and what can go wrong**
- More instances multiply database connections, as in the scenario. Cap pool sizes or use a connection proxy.
- Replica reads can be stale because of replication lag. A user may not see their own just-saved change, so read critical data from the primary.
- Caches can serve stale data and need an invalidation or expiry plan. A cold cache can also flood the database.
- Sharding is hard to undo. A bad key creates hot shards, cross-shard queries and joins get hard, and so do transactions.
- CQRS adds eventual consistency and operational complexity. Don't use it until simpler steps fail.

**How I'd monitor it**
- Service: p95/p99 latency, error rate, requests per instance, CPU, and autoscaling events.
- Database: CPU, active connections vs limit, slow query log, lock waits, and replica lag.
- Cache: hit ratio and eviction count.
- Splunk: search for "connection timeout" or "pool exhausted" errors grouped by host, and slow-query logs over time. Alert on p99 and on connection usage above about 80% of the limit.

**Follow-ups to expect**
- *Why not sticky sessions?* -> They tie users to one instance, so load is uneven and a crash loses the session. A shared store is safer.
- *How do you handle replica lag?* -> Send reads that must be fresh to the primary, or route a user to the primary briefly after they write.
- *How do you pick a shard key?* -> Pick one with high cardinality and even access, which matches most queries so they hit one shard. Avoid keys like date or country that create hot spots.

**60-second answer**
For the service, I make it stateless, move sessions to a shared cache, and run many copies behind a load balancer with autoscaling. I size the copies using requests per second times latency. The database holds the state, so I scale it step by step, and I measure first to find the real bottleneck. I start with indexes, query fixes and connection pool limits, then caching, then read replicas for read-heavy load. If writes or data size outgrow one primary, I shard by a well-chosen key. For very different read and write needs I consider CQRS. I watch for replica lag, stale caches, and too many connections from many instances. I track latency, DB CPU, connections and cache hit ratio to prove each step helped.

### Q5 [mid] Caching strategies and invalidation?
tags: caching, cache-aside, invalidation, ttl, cache-stampede, redis, caffeine, basics

**Start here: the concepts**
- **Cache:** a small, fast copy of data kept close to the application so we avoid repeating slow work, such as a database query. It exists because reads are far more frequent than writes, and the database is the scarce resource.
- **Cache hit / miss:** a hit means the data was found in the cache. A miss means it wasn't, so we go to the database.
- **Cache-aside:** the application checks the cache first. On a miss it reads the database and puts the result in the cache. On a write it updates the database, then deletes the cached key so the next read reloads fresh data.
- **Read-through:** the app talks only to the cache, and the cache layer loads from the database on a miss.
- **Write-through:** every write goes to the cache and the database together, synchronously. Reads stay fresh, but each write is slower.
- **Write-behind:** the write goes to the cache first and is saved to the database later, asynchronously. It is fast, but a cache crash can lose data not yet saved.
- **TTL (time to live):** an expiry time on each entry, so stale data can't live forever.
- **Explicit invalidation:** deleting or updating an entry the moment the source data changes, instead of waiting for the TTL.
- **Versioned keys:** the version is part of the key (`product:42:v7`). A change creates a new key, so old entries are simply never read again.
- **Cache stampede:** a hot entry expires and many requests miss at once, so all of them hit the database together.
- **Single-flight / lock:** only one request reloads the value while the others wait for its result.
- **Jittered TTL:** a small random amount added to each TTL so entries don't all expire together.
- **Serve-stale-while-revalidate:** return the slightly old value immediately while one background task refreshes it.
- **Two-level cache:** a local in-process cache (Caffeine, a Java caching library) in front of a shared cache (Redis). Local is the fastest but is per instance. Redis is shared by all instances.

**The live scenario**
A product catalog gets 5,000 reads/s. The database comfortably handles about 500 queries/s. With a 95% hit rate, only about 250 queries/s reach it. A hot product's entry expires, and in the next 200 ms about 1,000 requests miss together. Database latency goes from 5 ms to 2 s, and the incident starts. Later, a price change keeps showing the old price for 10 minutes, because only the TTL was cleaning it up.

**What the interviewer is really checking**
Whether you know that caching is easy and invalidation is the hard part. They want to hear you name the acceptable staleness, how you protect the database from stampedes, and the failure modes, not only "use Redis".

**How I answer it**
1. **Ask how stale the data may be.** A price can be wrong for seconds, an account balance almost never. That answer drives every other choice.
2. **Default to cache-aside.** It is simple, and the cache holds only what is actually read. The cache can fail and the system still works, just slower.
3. **Always set a TTL, and invalidate on write too.** The TTL is the safety net if an invalidation is missed. Explicit invalidation gives freshness. On a write, update the database first, then delete the key. Deleting is safer than updating the cache, because two concurrent writers could leave an older value in the cache.
4. **Use versioned keys when deletion is awkward**, such as many copies or derived entries. The new version is used immediately and old keys expire on their own.
5. **Pick write-through or write-behind only with a reason.** Write-through suits data that must be read fresh right after a write. Write-behind suits high write rates where losing a few writes is acceptable or a durable queue backs it.
6. **Prevent stampedes** with single-flight or a lock per key, jittered TTLs, and stale-while-revalidate. Together they mean the database sees one reload, not a thousand.
7. **Layer the caches** when latency matters: Caffeine locally with a short TTL (seconds), Redis behind it. Local copies are not shared, so broadcast invalidations (for example via Redis pub/sub) or keep local TTLs very short.

```java
Caffeine.newBuilder().maximumSize(10_000).expireAfterWrite(Duration.ofSeconds(30)).build();
```

**Trade-offs and what can go wrong**
- Staleness is the price of speed. Say how much you accept.
- Cache-aside has a race: a slow reader can write an old value after a writer deleted the key. A short TTL limits the damage.
- Write-behind can lose data on a crash.
- Local caches on different instances can disagree.
- Caching everything wastes memory. Caching null results needs a short TTL, or missing keys hit the database every time.
- A cold cache after a restart is a stampede in disguise, so warm hot keys first.

**How I'd monitor it**
- Hit ratio, miss rate and eviction count per cache. Alert if the hit ratio drops sharply.
- Database queries/s and p99 latency, to spot a stampede. Redis latency and memory.
- Loader-call counts per key, to confirm single-flight is working.
- In Splunk, search cache-miss logs by key and time, and look for spikes of the same key.

**Follow-ups to expect**
- *Why delete the key instead of updating it on write?* -> Two concurrent writers can leave an older value in the cache. Deleting makes the next read reload from the source of truth.
- *Cache-aside vs read-through?* -> The logic is the same, but in read-through the cache layer does the loading. In cache-aside your application code does it.
- *How do you invalidate a local Caffeine cache across 10 pods?* -> Publish an invalidation event (for example via Redis pub/sub or Kafka) that each pod listens to, and keep the local TTL short as a fallback.

**60-second answer**
First I ask how stale the data can be, because that drives everything. I default to cache-aside: read the cache, on a miss load from the database and store it, and on a write update the database and delete the key. Every entry has a TTL as a safety net, plus explicit invalidation for freshness, and versioned keys when deletion is awkward. Write-through gives fresh reads at slower writes, and write-behind is fast but can lose data. To avoid a stampede on a hot key I use single-flight so one request reloads, jittered TTLs, and serve-stale-while-revalidate. For speed I add a local Caffeine layer in front of Redis and watch hit ratio, database load and evictions. The famous quote says cache invalidation is one of the two hard things in computing, and a clear staleness budget is how I handle it.

### Q6 [mid] Load balancing algorithms and levels?
tags: load-balancing, l4, l7, round-robin, least-connections, consistent-hashing, basics

**Start here: the concepts**
- **Load balancer:** a component that sits in front of several copies of a service and spreads incoming requests across them. It exists so no single server is overloaded and so one server dying does not take the service down.
- **Backend / instance:** one running copy of the service that the load balancer can send traffic to.
- **L4 (transport level) load balancing:** the balancer looks only at TCP/UDP details (IP addresses and ports) and forwards the connection without reading the contents. It is fast and simple, but it cannot tell `/orders` from `/payments`.
- **L7 (application level) load balancing:** the balancer reads the HTTP request (path, headers, cookies) and decides based on that. For example, `/api/orders` goes to the order service and a `X-Beta: true` header goes to a canary group. It can also terminate TLS and rewrite requests. It costs more CPU than L4.
- **Round robin:** send request 1 to server A, 2 to B, 3 to C, then start again.
- **Weighted:** give bigger servers a bigger share, for example weight 3 vs 1. It is a modifier on round robin or least connections.
- **Least connections:** send the next request to the server with the fewest in-flight requests, so slow servers naturally get less.
- **Consistent hashing:** hash a key (user id, cache key) onto a ring of servers so the same key always lands on the same server. When a server is added or removed, only a small fraction of keys move. It suits caches and per-user state.
- **Health check:** the balancer regularly probes each backend (for example `GET /health`) and stops sending traffic to failing ones.
- **Connection draining:** when removing an instance (a deploy, scale-down), stop giving it new requests but let in-flight ones finish.

**The live scenario**
An order service runs 6 instances behind a balancer at about 3,000 requests/s using round robin. One instance hits long garbage-collection pauses and gets slow. Round robin keeps sending it 1/6 of traffic (500 requests/s), so requests queue up there. p99 latency rises from 200 ms to 4 s and about 1/6 of users see timeouts. Switching to least connections cut p99 back to about 300 ms, because the slow node held more open requests and so received fewer new ones. During the next deploy, instances were killed instantly and in-flight payments returned 502 errors. Connection draining fixed that.

**What the interviewer is really checking**
Whether you know that the level (L4 vs L7) and the algorithm are separate choices, and whether you pick them from the workload (stateless, cached, uneven request cost) and handle failure and deploys, not just recite names.

**How I answer it**
1. **Pick the level first.** Use L4 when I need raw speed or non-HTTP protocols. Use L7 when I need routing by path or header, TLS termination, or canary releases. L7 can read the request, and L4 cannot.
2. **Default to round robin for identical, stateless, short requests.** It is simple and fair when every request costs about the same.
3. **Use weighted when servers differ.** A bigger machine or a canary with 5% traffic needs an explicit share.
4. **Use least connections when request cost varies** (long uploads, slow reports). It adapts to real load instead of assuming equality.
5. **Use consistent hashing when the same key should hit the same node,** for example local caches or sticky sessions. Only a small share of keys move when nodes change, so the caches stay warm.
6. **Always add health checks.** Without them, the balancer keeps sending traffic to a dead node. Make the check reflect real readiness, not just "process is up".
7. **Use connection draining on every deploy or scale-in,** so in-flight requests finish instead of failing.

**Trade-offs and what can go wrong**
- Round robin ignores load, so one slow node hurts everyone.
- Consistent hashing can create hot spots if one key is very popular. Virtual nodes help spread load more evenly.
- Sticky sessions hide a design problem: if the node dies, the user's state is lost. Prefer stateless services with shared session storage.
- Health checks that are too aggressive cause flapping (nodes removed and re-added repeatedly). Checks that are too lax keep bad nodes in rotation.
- The balancer itself can be a single point of failure, so run it redundantly.
- L7 adds latency and CPU cost compared with L4.

**How I'd monitor it**
- Per-backend request count, active connections, 5xx rate and p99 latency, to spot skew between instances.
- Healthy-host count with an alert when it drops below a threshold.
- Balancer access logs in Splunk, grouped by backend address, to compare error and latency per node.
- Deploy dashboards that show 502/503 spikes, which indicate that draining is missing or too short.

**Follow-ups to expect**
- *Why not always use least connections?* -> It needs the balancer to track connection state, and it can overload a freshly started node that has zero connections. Slow-start ramping helps.
- *How do you handle sessions with a load balancer?* -> Prefer stateless services with shared storage such as Redis. If stickiness is unavoidable, use cookie or consistent-hash affinity.
- *What is a health check versus a readiness check?* -> Liveness asks "is the process alive?" and readiness asks "can it serve traffic now?". The balancer should use readiness.

**60-second answer**
A load balancer spreads requests across several copies of a service and removes failed ones. L4 balances at the TCP level and is fast but blind to content. L7 reads HTTP, so it can route by path or header and terminate TLS. For algorithms, round robin works for similar short requests, weighted handles unequal servers, and least connections adapts when request cost varies. Consistent hashing sends the same key to the same node, which keeps caches warm and moves few keys when nodes change. I always add health checks to eject bad nodes and connection draining so deploys do not drop in-flight requests. I watch per-node latency, errors and healthy-host count to catch skew early.

### Q7 [mid] How do you achieve idempotency across a distributed flow?
tags: idempotency, distributed-systems, at-least-once, retries, kafka, unique-constraint, basics

**Start here: the concepts**
- **Idempotent operation:** doing it twice has the same effect as doing it once. "Set status to PAID" is idempotent. "Add 100 to balance" is not.
- **Why it matters:** networks fail in ambiguous ways. If a call times out, you don't know whether it ran, so the caller retries. Without idempotency, a retry can charge a customer twice.
- **At-least-once delivery:** the system guarantees a message arrives one or more times, never zero. Kafka consumers and HTTP retries behave this way. Duplicates are the price of not losing anything.
- **Effectively once:** true exactly-once across separate services is not realistic. Instead we accept duplicates and make processing them harmless, so the outcome looks like one execution.
- **Idempotency key (command id):** a unique id, usually a UUID, created once by the originator of a request and reused on every retry of that same request. It lets a receiver recognise "I've seen this".
- **Unique constraint:** a database rule that rejects a second row with the same key. The database enforces it atomically, so two simultaneous duplicates cannot both win.

**The live scenario**
A payments flow handles about 2,000 orders a minute. The mobile app calls Order Service, which calls Payment Service, which calls an external card gateway. During a slow gateway period, about 1.5% of calls time out at 2 seconds and the app retries. That is roughly 30 retries a minute. Some of the original requests had actually succeeded. Customers were charged twice, and support received about 40 tickets in an hour. A Kafka consumer rebalance also redelivered messages, which caused duplicate "payment captured" events downstream.

**What the interviewer is really checking**
Whether you understand that retries and redelivery are normal, so safety must be designed in. They also want to see that you know where the dedupe record lives, how races are handled, and how to cover third-party calls.

**How I answer it**
1. **Generate one id per business command at the edge.** The client or API gateway creates it, and every retry reuses it. If each hop made a new id, retries would look like new work.
2. **Pass the id through every hop,** including HTTP headers and Kafka message headers or keys. Every service can then dedupe on the same identity.
3. **Each service keeps a processed-ids table with a unique constraint,** and stores the result next to the id. A duplicate returns the stored result instead of re-running. The caller gets the same answer as the first time.
4. **Insert the id in the same database transaction as the business change.** If the id were saved separately, a crash between the two steps would either lose the work or skip it forever on retry.
   ```sql
   INSERT INTO processed_command(cmd_id, result) VALUES (?, ?) -- PK/unique on cmd_id
   ```
5. **Let the unique constraint settle races.** Two identical requests arriving at once cannot both insert. The loser catches the duplicate-key error and returns the stored result. A plain "check, then insert" has a race window.
6. **Use the third party's idempotency key for outside side effects.** Gateways such as Stripe accept an idempotency header. Send your command id there, because you cannot put your table inside their system.
7. **Publish events reliably with the outbox pattern.** Write the event to an outbox table in the same transaction as the business change. A relay then publishes it, at-least-once, and consumers dedupe by id.
8. **Combine the pieces.** Retries and redelivery give at-least-once, and the dedupe steps make duplicates harmless. That is effectively once.

**Trade-offs and what can go wrong**
- The processed-ids table grows, so add a TTL or purge window. It must be longer than the longest realistic retry or replay period.
- A retry that arrives while the first attempt is still running needs a defined behaviour. Use an "in progress" status and return 409 or wait.
- Reusing a key with a different payload is a bug. Detect it by storing a request hash.
- Kafka's idempotent producer only stops duplicates caused by producer retries. It does not stop consumer reprocessing after a rebalance, so consumers still need dedupe.
- Naturally idempotent designs, like "set X" or upserts, are cheaper than tracking ids where they fit.

**How I'd monitor it**
- Count duplicate hits per service (the "duplicate command ignored" rate). A sudden spike means upstream timeouts or rebalances.
- Search Splunk by command id to trace one request across services.
- Run a reconciliation job that compares charges at the gateway with local payments, and alert on any mismatch.
- Track retry rate, timeout rate and consumer lag.

**Follow-ups to expect**
- *Why not just check whether the order exists first?* -> Check-then-act races under concurrency. Only an atomic unique constraint is safe.
- *How long do you keep ids?* -> Longer than the maximum retry or replay window, for example days. Then purge or expire them.
- *Does Kafka exactly-once solve this?* -> Only inside Kafka (transactions, read-process-write to Kafka). Calls to databases or external APIs still need idempotency.

**60-second answer**
Retries and redelivery are normal, so I make operations safe to repeat. The originator creates one unique id per business command and reuses it on every retry. It travels through every service. Each service records the id in a table with a unique constraint, in the same transaction as its business change, and stores the result. A duplicate returns the saved result, and the constraint settles simultaneous duplicates. For third-party calls I pass the id as their idempotency key. Events go out through an outbox. Delivery is at-least-once, and with idempotent handling the result is effectively once. I monitor duplicate rates and reconcile against the payment gateway.

### Q8 [mid] What are consistent hashing and why is it used?
tags: consistent-hashing, distributed-systems, caching, partitioning, cassandra, couchbase, basics

**Start here: the concepts**
- **Sharding (partitioning):** splitting data across several machines because one cannot hold it all or serve all the traffic. Each key must always map to the same machine so we can find it again.
- **Hash function:** turns any key (like `user:42`) into a number. The same key always gives the same number, and the numbers are spread fairly evenly.
- **Naive approach, modulo:** `node = hash(key) % N`, where N is the node count. It is simple, but when N changes, the result changes for almost every key.
- **Hash ring:** the range of hash values bent into a circle. Each node gets a position on the circle, and each key gets a position from its hash.
- **Clockwise rule:** a key belongs to the first node you meet walking clockwise from the key's position.
- **Virtual nodes (vnodes):** each physical server takes many positions on the ring, for example 100-256 small slices instead of one. This spreads load evenly and lets a new node take small pieces from everyone.
- **Rebalancing:** moving data when nodes join or leave. The goal is to move as little as possible.

**The live scenario**
We run 4 cache servers at 20,000 reads/s with a 95% hit rate, so the database sees about 1,000 reads/s. Before a sale we add a 5th cache node. The router uses `hash % N`, and N changes from 4 to 5. About 80% of keys now map to a different node, where they are not cached yet. The hit rate falls to roughly 20%, and the database suddenly gets around 16,000 reads/s. Latency climbs from 5 ms to seconds, and the database nearly falls over. With consistent hashing, adding the 5th node would remap only about 1/5 of the keys (~20%) and leave the rest warm.

**What the interviewer is really checking**
Whether you understand the problem it solves (mass key movement when the cluster size changes) and can explain the ring, virtual nodes and real uses. They also want to see that you know it is a family of ideas, not one exact algorithm.

**How I answer it**
1. **Start with the problem.** With `hash % N`, changing N remaps most keys. In a cache that means a wave of misses, and in a database it means moving huge amounts of data.
2. **Describe the ring.** Hash both nodes (say, by IP) and keys onto the same circular space. A key goes to the next node clockwise. This makes ownership depend on neighbours, not on the total count.
3. **Explain what happens on a change.** When a node is added, it takes over only the arc between itself and its predecessor, so only about 1/N of the keys move, and they move only to the new node. When a node dies, its keys go to the next node clockwise and nothing else moves.
4. **Fix the uneven load with virtual nodes.** With one point per server, arcs are random sizes, so one node may own far more keys. Giving each server many points averages this out. A bigger server can get more vnodes. When a node fails, its load spreads over many nodes instead of dumping on one neighbour.
5. **Name real uses.** Cache client routing, load balancers (so the same client hits the same backend), and Cassandra, which uses a token ring with vnodes. Couchbase works slightly differently: it hashes each key into one of a fixed set of vBuckets (1024 by default on most platforms) and keeps a cluster map from vBuckets to nodes. It has the same goal, moving few keys when nodes change, but it is a fixed-partition map, not a literal ring.

**Trade-offs and what can go wrong**
- Without vnodes, distribution is uneven and a failed node overloads its neighbour.
- A hot key (one very popular item) is still on one node. Hashing spreads keys, not traffic per key.
- Every client or router must see the same node list. If views differ, keys are routed inconsistently.
- Ring lookups need a sorted structure (binary search or tree), which is slightly more complex than modulo.
- Data stores still have to copy the moved data, so rebalancing uses network and disk and needs throttling.
- Fixed-partition schemes (like vBuckets) are simpler to reason about but need the partition count chosen up front.

**How I'd monitor it**
- Cache hit ratio and database QPS during any node change. A sudden drop means too many keys moved.
- Keys, memory and requests per node. A big skew means too few vnodes or hot keys.
- Rebalance or streaming progress and bytes moved (for example `nodetool status` and `nodetool netstats` in Cassandra, or the rebalance view in the Couchbase UI).
- Splunk: search for cache-miss spikes or timeouts in the minutes after a scaling event, and alert on per-node error rates.

**Follow-ups to expect**
- *Why not just use modulo?* -> A change in N remaps most keys, causing a miss storm or massive data movement.
- *How many vnodes should a node have?* -> Enough to even out load (often tens to hundreds). More vnodes smooth the load but add metadata and make repairs and streaming more complex.
- *Does it solve hot keys?* -> No. Use replication of hot keys, local caching or key splitting.

**60-second answer**
Consistent hashing is a way to decide which node owns which key so that adding or removing a node moves very few keys. With plain `hash % N`, changing N remaps almost everything, which empties a cache or forces a huge data shuffle. Instead I put nodes and keys on a hash ring, and each key belongs to the next node clockwise. When a node joins or leaves, only about 1/N of the keys move. To keep load even I give each server many virtual nodes, so it owns lots of small slices. Cassandra uses this idea with its token ring, caches and load balancers use it for routing, and Couchbase achieves the same goal with a fixed set of vBuckets mapped to nodes.

### Q9 [mid] Explain leader election, consensus and distributed locks.
tags: leader-election, consensus, raft, distributed-lock, fencing-token, zookeeper, basics

**Start here: the concepts**
- **Leader election:** a group of nodes picks exactly one node to do a special job, such as accepting writes or running a scheduled task. It exists so that two nodes never do that job at once.
- **Consensus:** a protocol that lets several nodes agree on one value (for example "node B is leader") even if some nodes crash or messages are delayed. It works by requiring a **majority (quorum)** to accept a value. Two majorities always overlap, so two conflicting decisions cannot both win.
- **Raft and Paxos:** well-known consensus algorithms. Raft is the easier one to learn. etcd uses Raft, and Kafka's KRaft mode uses a Raft-based quorum instead of ZooKeeper. ZooKeeper uses its own related protocol (ZAB), not Raft or Paxos.
- **Distributed lock:** a rule saying "only one process across many servers may do X right now", for example run a nightly job or update one record.
- **Lease:** a lock that expires automatically after a time limit. If the holder crashes, the lock frees itself instead of staying stuck forever.
- **Fencing token:** a number that increases every time the lock is granted. The protected resource remembers the highest number it has seen and rejects anything lower.
- **Idempotency:** doing the same operation twice has the same effect as doing it once.

**The live scenario**
A billing service runs on 6 pods. A nightly job must charge 200,000 customers exactly once. The team used a Redis lock with a 30-second expiry. One pod hit a 45-second JVM GC pause. Its lock expired and a second pod took over. The first pod woke up, still believed it held the lock, and kept charging. About 1,800 customers were charged twice, which led to refunds and support tickets. The lock was not the real problem. The missing protection at the database was.

**What the interviewer is really checking**
Whether you know that a lock alone cannot guarantee safety, because processes pause and clocks drift. They also want to see that you separate "who is leader" (consensus) from "who may touch this data" (fencing), and that you prefer designs that need no lock.

**How I answer it**
1. **Define the problem first.** Several nodes, failures are normal, and we need one decision-maker. Without this, people reach for a lock without knowing what it must guarantee.
2. **Leader election rests on consensus.** A majority must agree on the leader, so a network split cannot produce two leaders. The minority side stops serving. In practice I use etcd, ZooKeeper, or Kafka's KRaft controllers rather than writing Raft myself, because the edge cases are very hard.
3. **For app-level locks, use a lease.** The lock expires, so a crashed holder cannot block everyone forever. Common stores are Redis, a database row, etcd, or ZooKeeper.
4. **Add a fencing token, because a lease alone is unsafe.** A holder can pause (GC, network stall) past its expiry and still think it owns the lock. Every write carries the token, and the database rejects stale ones:
```sql
UPDATE account SET balance=?, last_token=? WHERE id=? AND last_token < ?
```
5. **Pick a store that can supply the token.** etcd has a revision number, ZooKeeper has sequence nodes, and a database can use an incrementing counter or version column. Plain Redis `SET key value NX PX 30000` gives mutual exclusion with expiry, but no token. A single Redis node can also lose the lock on failover, so it is fine for efficiency-only locks, not for correctness.
6. **Prefer avoiding locks.** Partition the work so each pod owns a slice (for example by customer ID hash, as Kafka consumer groups do), and make operations idempotent with a unique charge ID. Then a double run is harmless.

**Trade-offs and what can go wrong**
- Consensus needs a majority, so a 3-node cluster tolerates 1 failure and a 5-node cluster tolerates 2. Every write also costs extra network round trips.
- Too short a lease causes false takeovers. Too long delays recovery after a crash.
- Relying on clocks across machines is risky, because clocks drift.
- Running a coordination cluster is extra operational work.
- The common mistake is "I took the lock, so I am safe." A paused holder breaks that.

**How I'd monitor it**
- Leader-change count and current leader per group. Frequent flapping means network or GC trouble.
- Lock acquisition wait time, lock hold time, and lease-expiry-while-working events.
- Rejected-stale-token count, which should be low but visible.
- Splunk search for "lock lost" or "token rejected" by job ID.
- For etcd or KRaft, quorum health and commit latency, with alerts on lost quorum.
- A duplicate-charge reconciliation check.

**Follow-ups to expect**
- *Why use an odd number of nodes?* -> A majority needs more than half. 4 nodes tolerate only 1 failure, the same as 3, so the extra node adds cost with no benefit.
- *What is split-brain?* -> Two parts of a cluster each think they are the leader. Majority quorum prevents it, because only one side can hold a majority.
- *Is Redlock safe?* -> It is debated. Because of pauses and clock assumptions, I would not trust it for correctness without fencing.

**60-second answer**
Consensus, such as Raft, lets nodes agree on one value, like who the leader is, even when some fail. It works because a majority must agree, so a network split cannot create two leaders. Systems like etcd, ZooKeeper and Kafka KRaft are built on it, so I use them rather than writing my own. For an application lock I use a lease that expires automatically, so a crash cannot block everyone. But a paused process can wake up after its lease expired and still write, so I add a fencing token, an increasing number the database checks and rejects if it is stale. Even better, I avoid locks by partitioning work and making operations idempotent.

### Q10 [senior] What happens with clock skew and ordering of events?
tags: clock-skew, event-ordering, kafka-offsets, versioning, distributed-systems, last-write-wins, basics

**Start here: the concepts**
- **Wall clock**: the time a machine reads from its own hardware clock, usually corrected by NTP (a protocol that syncs clocks over the network). Two machines never agree exactly.
- **Clock skew**: the difference between two machines' clocks. It is often a few milliseconds, but a VM pause, a failed NTP sync or a bad leap-second adjustment can push it to hundreds of milliseconds or more. Clocks can also jump backwards.
- **Concurrent updates**: two writes where neither writer knew about the other. "Which came first?" may have no true answer.
- **Last-write-wins (LWW)**: when two versions conflict, keep the one with the higher timestamp. Cassandra does this per cell by default.
- **Version number**: a counter stored with the record. Each update says "I am changing version 7 into 8". If the stored version is no longer 7, the write is rejected, so nothing is silently overwritten.
- **Kafka offset**: a sequential position number of a message inside one partition. Order is guaranteed only within that partition, not across partitions.
- **Logical clock**: a counter that tracks cause and effect instead of real time. A **vector clock** is a set of such counters, one per writer. It can tell "B happened after A" from "A and B were concurrent".
- **Single writer per key**: all updates for one entity go through one place, for example Kafka partitioning by key. That place defines the order.

**The live scenario**
A profile service runs 3 instances and handles about 2,000 updates/sec into Cassandra. One VM's clock drifts 300 ms ahead after an NTP problem. A user changes a phone number, then corrects it 200 ms later. The first request hit the fast-clock node and got timestamp T+300. The second hit a correct node and got T+200. LWW kept the **older** value. About 0.1% of updates were affected, which is 2 per second. There were no errors, only support tickets saying "my change didn't save".

**What the interviewer is really checking**
Whether you know that physical time cannot order events across machines. They also want to see that you can name concrete alternatives and know their limits, such as per-partition ordering and silent data loss under LWW.

**How I answer it**
1. **State the rule: never order concurrent updates by timestamp alone.** Each machine's clock is slightly wrong in a different way, so timestamps from different machines are not comparable at fine granularity.
2. **Prefer a single writer per key.** Publish updates to Kafka keyed by entity ID. All events for one key land in one partition, and the offset gives a total order for that key. The limit is that this order exists only inside a partition, so never compare offsets across partitions or topics.
3. **If several writers are unavoidable, use per-entity version numbers (optimistic concurrency).** The write succeeds only if the version it read is still current:
   `UPDATE profile SET phone=?, ver=ver+1 WHERE id=? AND ver=?`
   Zero rows updated means someone else got in first. The caller re-reads and retries, or merges.
4. **If replicas accept writes independently, use logical or vector clocks.** They detect "these two were concurrent", and you can then merge or ask the user. They do not tell you which one is "right".
5. **If you must use timestamps, treat them as a tiebreaker, not the truth.** Use a time source you control, such as a database server's time, and keep NTP healthy. Accept that LWW can drop an update and only use it where that is acceptable, such as a "last seen" field.
6. **Remember Kafka's own timestamps.** A message's timestamp is either producer-set (CreateTime) or broker-set (LogAppendTime). Neither should be used to order across partitions. Use offsets within a partition.

**Trade-offs and what can go wrong**
- LWW is simple and fast but loses data silently, with no error or log line.
- Version checks cost a retry path and add contention on hot keys.
- Single-writer ordering limits parallelism to the number of partitions, and a hot key can overload one partition.
- Vector clocks grow with the number of writers and push conflict resolution onto application code.
- Common mistakes: sorting events by `createdAt` in a consumer, assuming ordering across partitions, and trusting "NTP is fine" without measuring it.

**How I'd monitor it**
- Alert on clock offset per host (for example `chronyc tracking` or node_exporter's `node_timex_offset_seconds`) when it passes a small threshold.
- Count optimistic-lock failures and retries per second. A spike means contention or a bug.
- Search Splunk for events where a new version or timestamp is lower than the stored one, and for out-of-order arrivals per key.
- Watch Kafka consumer lag per partition, and key skew where one partition is much busier than the others.

**Follow-ups to expect**
- *Does Kafka guarantee global ordering?* -> No. It guarantees order only within a partition. Use the same key for events that must stay ordered.
- *Can a vector clock tell you which write is correct?* -> No. It only tells you whether one write happened after the other or whether they were concurrent. You still need a merge rule.
- *How do you reduce skew rather than work around it?* -> Run NTP or chrony on every host and alert on offset. Some systems go further and use bounded-uncertainty clocks, as Google Spanner does with TrueTime.

**60-second answer**
Each machine's clock is slightly different, and it can jump, so I never order concurrent updates by timestamp alone. Last-write-wins by timestamp can silently keep the older value and drop the newer one. My first choice is a single writer per key: I key Kafka messages by entity ID so they share a partition, and the offset gives the order, though only within that partition. When several writers are unavoidable, I keep a version number on each record and make updates conditional on it, so a stale write fails instead of overwriting. For replicated stores I use logical or vector clocks to detect conflicts and then merge them. I monitor clock offset, version-conflict counts and consumer lag per partition.

### Q11 [senior] Backpressure, load shedding and bulkheads?
tags: backpressure, load-shedding, bulkhead, resilience, rate-limiting, kafka, system-design, basics

**Start here: the concepts**
- **Overload:** work arrives faster than a service can finish it. Queues grow, latency rises, memory and threads fill, and eventually the service falls over. All three ideas below are ways to survive this.
- **Backpressure:** the slow part of a pipeline tells the fast part to slow down instead of letting work pile up. Examples are a bounded queue that blocks or rejects when full, a reactive-streams subscriber that requests only N items at a time, and TCP flow control. It exists so the slowness shows up at the source rather than as an out-of-memory crash in the middle.
- **Bounded queue:** a queue with a fixed maximum size. An unbounded queue hides overload until memory runs out.
- **Kafka and backpressure:** Kafka consumers *pull* messages at their own pace, so a slow consumer does not crash. The messages wait in the log and *consumer lag* grows. Lag does not slow producers; the broker keeps accepting writes. Scaling consumers when lag grows is autoscaling, which adds capacity. It is not backpressure. Real backpressure on a Kafka path means limiting what the consumer takes in flight, for example by pausing partitions, or limiting the upstream producer.
- **Load shedding:** deliberately refusing some work early so the rest succeeds. You choose what to drop, such as low-priority or anonymous traffic, and fail it fast and cheaply. It exists because a service that tries to serve everyone during overload often serves no one.
- **HTTP 429 vs 503:** 429 means "you are sending too much". 503 means "I am overloaded". A `Retry-After` header tells clients when to come back.
- **Bulkhead:** named after the watertight compartments in a ship's hull. You give each dependency or tenant its own thread pool, queue or connection pool, so a leak in one compartment does not sink the ship.

**The live scenario**
A checkout service handles 500 req/s, and each request calls a recommendations service. Normally that call takes 50 ms. By Little's Law (concurrent calls = rate × latency), that is 500 × 0.05 = about 25 threads busy. During a sale, recommendations degrades to 8 s. Now 500 × 8 = 4,000 threads would be needed, but the shared pool has only 200. All 200 threads sit waiting, and payments, which never needed recommendations, stop responding. Checkout is down because of an optional feature.

**What the interviewer is really checking**
Whether you understand that overload spreads through shared resources and queues. Also whether you can name three different tools, say which problem each solves, and combine them.

**How I answer it**
1. **Find the shared resource that fails first.** It is usually threads, connections or queue memory. Little's Law shows how slow dependencies multiply concurrency.
2. **Apply bulkheads to isolate.** Give recommendations its own small pool, for example 20 threads and a short queue. When it is full, calls fail immediately and checkout continues without recommendations. Isolation limits the blast radius.
   ```java
   new ThreadPoolExecutor(20, 20, 0, SECONDS, new ArrayBlockingQueue<>(50), new AbortPolicy());
   ```
3. **Use bounded queues for backpressure.** Every queue gets a limit and a defined behaviour when full: block, reject or drop. This pushes the problem back toward the caller while it is still small.
4. **Shed load at the edge.** Rank traffic by importance and reject the least important first (browse before pay) with 429 or 503 plus `Retry-After`. Reject early, before doing expensive work, because rejection must cost almost nothing.
5. **Add timeouts and a fallback.** A bulkhead without a timeout still holds its threads for 8 s. Return a default list of recommendations when the call fails.
6. **Scale as the slower fix.** Autoscaling takes minutes, while these protections work in milliseconds.

**Trade-offs and what can go wrong**
- Shedding means some users get errors on purpose. You must decide the priorities in advance with the business.
- Small bulkheads waste capacity when idle, and badly sized ones reject healthy traffic.
- Clients that retry immediately turn shedding into a retry storm. Use exponential backoff with jitter.
- Unbounded queues and unlimited retries quietly defeat everything above.
- Blocking producers can move the stall upstream and cause a wider outage, so decide where it is safe to block.

**How I'd monitor it**
- Thread pool active count, queue depth and rejected-task count for each bulkhead.
- Rate of 429/503 responses, split by traffic class, and p99 latency per dependency.
- Kafka consumer lag per partition, with an alert when it keeps growing.
- Splunk: search for rejection and timeout log lines grouped by dependency, and alert on a sudden rise.

**Follow-ups to expect**
- *Bulkhead vs circuit breaker?* -> A bulkhead caps how many resources a dependency can use. A circuit breaker stops calling a dependency that keeps failing. Use both.
- *Rate limiting vs load shedding?* -> Rate limiting enforces a per-client quota at all times. Shedding reacts to the system's current overload and drops by priority.
- *Why not just autoscale?* -> It is too slow for sudden spikes and can overload a shared downstream like the database. Protection comes first, then scaling.

**60-second answer**
Overload spreads through shared queues, threads and connections, so I use three tools. Backpressure makes the slow part push back with bounded queues instead of piling up unlimited work. Kafka consumers pull, so lag simply grows, and scaling on lag is autoscaling, not backpressure. Load shedding rejects the least important requests early with 429 or 503 and a `Retry-After`, so core traffic like payments stays healthy. Bulkheads give each dependency or tenant its own small pool, so one slow service, say recommendations at 8 seconds, cannot use up all 200 threads. I add timeouts, fallbacks and jittered retries, and I watch pool saturation, rejections, p99 latency and consumer lag.

### Q12 [senior] Retry storms and thundering herd - prevention?
tags: resilience, retry, backoff, jitter, circuit-breaker, cache-stampede, basics

**Start here: the concepts**
- **Retry:** calling again after a failure. It helps with brief glitches, but it adds load to a service that may already be struggling.
- **Retry storm:** many clients retry at once, and the extra traffic keeps the struggling service down. A small outage becomes a long one.
- **Thundering herd:** many clients do the same thing at the same instant, such as all reloading a cache entry the moment it expires.
- **Exponential backoff:** wait longer after each failure (for example 100 ms, 200 ms, 400 ms). This gives the server room to recover.
- **Jitter:** a random amount added to the wait. Without it, clients that failed together retry together, in synchronized waves.
- **Retry budget:** a cap on retries as a share of normal traffic (for example 10%). When the budget is spent, you fail fast instead of retrying.
- **Circuit breaker:** a switch that "opens" after many failures and rejects calls immediately for a while. It then lets a few test calls through to check for recovery.
- **Deadline propagation:** the caller's remaining time is passed down the call chain, so no layer works on a request the user has already given up on.
- **Cache stampede:** a herd on cache expiry. A hot key expires and thousands of requests hit the database to rebuild it.
- **Idempotent:** safe to run twice with the same result. Only idempotent calls should be retried automatically.

**The live scenario**
An order service handles 2,000 requests/s. A database blips for 5 seconds. The gateway, the service and the client library each retry up to 3 times, so one user action can become up to 27 database calls. Load jumps from 2,000 to over 10,000 attempts/s and the database never recovers. A 5-second blip becomes a 20-minute outage. Separately, 50,000 product keys were cached with an identical 60-minute TTL, so they all expired together and the database took a spike it normally never sees.

**What the interviewer is really checking**
Whether you see that retries multiply load and so can cause outages, and whether you can layer several defenses (client, system and cache) instead of just saying "add retries".

**How I answer it**
1. **Retry in one layer only, usually the one closest to the caller.** Every extra layer multiplies attempts (3 × 3 × 3 = 27). Other layers fail fast and pass the error up.
2. **Use exponential backoff with jitter.** Backoff spreads retries over time, and jitter breaks the synchronization between clients. Full jitter is the simple form: `sleep = random(0, min(cap, base * 2^attempt))`.
3. **Add a retry budget.** Backoff slows each client but doesn't limit the total. A budget caps retries at about 10% of traffic, so the worst case is 1.1× load, not 3× or 27×.
4. **Wrap the dependency in a circuit breaker.** When failures are clearly not transient, stop calling. This protects the dependency and frees your threads instead of letting them wait on timeouts.
5. **Set deadlines and propagate them.** If 800 ms of a 1 s budget is used, downstream services shouldn't start a 3-second retry loop for a caller who has left.
6. **Retry only safe errors.** Retry timeouts and 503s on idempotent calls, with idempotency keys for writes. Never retry 4xx validation errors.
7. **Prevent cache herds.** Use a lock or "single flight" so one request rebuilds the key while the others wait or get slightly stale data. Add random jitter to TTLs (for example 60 min ± 10%) so keys don't expire together.

**Trade-offs and what can go wrong**
- Backoff and breakers add latency and can reject requests that would have succeeded.
- A badly tuned breaker flaps between open and closed.
- Retry budgets mean some users see errors sooner. That is deliberate, because you are trading a few failures for overall survival.
- Cache locks can create waiting queues if the rebuild is slow, so give lock waits a timeout.
- Retrying non-idempotent writes causes duplicate charges or orders.
- Jitter that is too small still leaves clients synchronized.

**How I'd monitor it**
- Retry rate and retry-to-request ratio per service.
- Breaker state changes (open/half-open/closed).
- Downstream request rate compared with upstream. A ratio above 1.1 means amplification.
- p99 latency, timeout counts, and cache hit ratio with database QPS at expiry boundaries.
- Splunk: search for retry-attempt logs grouped by trace ID to spot requests with many attempts.
- Alert when the retry ratio exceeds the budget.

**Follow-ups to expect**
- *Why is jitter needed if you already have exponential backoff?* -> Backoff alone keeps clients that failed together retrying together, just at longer intervals. Jitter spreads them out.
- *Retry budget vs circuit breaker?* -> The budget limits how much retry traffic you add. The breaker stops calls altogether when the dependency is clearly down. You use both.
- *How do you stop a cache stampede on one very hot key?* -> Single-flight or a lock so one request rebuilds it, serve stale data while refreshing, and jitter the TTL.

**60-second answer**
Retries help with brief glitches, but they multiply load. If three layers each retry three times, one request becomes 27. So I retry in only one layer, with exponential backoff and random jitter so clients don't retry in sync. I add a retry budget of about 10% of traffic and a circuit breaker to stop calling a dependency that is clearly down. I propagate deadlines so no one works on abandoned requests, and I only retry idempotent calls. For cache herds, I use a lock so one request rebuilds a key, and I give TTLs random jitter so keys don't expire together. I watch the retry ratio, breaker state and database load at expiry times.

### Q13 [senior] How do you handle hot partitions / hot keys?
tags: kafka, partitioning, hot-key, load-skew, scalability, nosql, basics

**Start here: the concepts**
- **Partition:** a slice of a topic (Kafka) or of a table's data (Cassandra, Couchbase, MongoDB shards). Data is split so that many machines share the work.
- **Partition key:** the value (for example `tenantId`) that is hashed to choose the partition. Same key, same partition, which gives ordering per key. In Kafka, the default partitioner hashes the key and takes the result modulo the partition count.
- **Hot partition / hot key:** one partition gets far more traffic than the others, usually because one key is very popular. The cluster looks idle overall while one node or consumer is overloaded.
- **Why it hurts:** in Kafka, one partition is read by only one consumer in a group. Adding consumers does not help the hot partition. Lag grows (lag = messages written but not yet processed).
- **Cardinality:** the number of distinct key values. Low cardinality means few buckets, so uneven spread is likely.
- **Salting:** adding a small suffix to the key so one logical key spreads across several partitions.

**The live scenario**
A SaaS platform has a 12-partition `events` topic at about 60k msg/s, keyed by `tenantId`. One enterprise tenant sends about 40% of the traffic, around 24k msg/s, all into one partition. Each consumer handles about 5k msg/s, so that partition's lag grows by about 19k msg/s. Within minutes, that tenant's dashboards are 20 minutes stale. The other 11 partitions are nearly idle, and adding consumers changes nothing. (Numbers are illustrative.)

**What the interviewer is really checking**
Whether you can find skew with data instead of guessing, and whether you understand the trade-off between spreading load and keeping ordering.

**How I answer it**
1. **Confirm it is a hot partition.** Compare per-partition message rate, bytes and consumer lag. One outlier means a hot key. Uniform lag means you need more capacity, not a key fix.
2. **Find the key.** Sample keys on the hot partition. Fixing a symptom without knowing the key leads to wrong fixes.
3. **Choose a higher-cardinality partition key.** If ordering is only needed per order, key by `orderId`, not `tenantId`. More distinct values means a more even hash spread. This is the cleanest fix.
4. **If you must keep the tenant grouping, split it by sub-key or salt it, but only when ordering allows.** Ordering holds only within one partition, so a split key loses ordering across the pieces. Order inside each sub-key is kept:
   ```java
   key = tenantId + "#" + Math.floorMod(orderId.hashCode(), 8); // tenant spread over 8 partitions
   ```
5. **For hot reads, use local caching.** If the hot key is read heavily (a database partition or a popular record), an in-process cache with a short TTL absorbs most reads before they reach the partition. This helps reads, not Kafka write skew.
6. **Rate limit heavy tenants.** Quotas or throttling stop one tenant from taking a shared resource. The cost is that you slow a paying customer, so agree on this with the business.
7. **Give top tenants dedicated partitions or queues.** Route known giants to their own topic or partitions with their own consumers. This isolates them, but needs a routing rule and ongoing maintenance.

**Trade-offs and what can go wrong**
- Salting and sub-keys break strict per-key ordering, and consumers that aggregate per tenant must now merge several partitions.
- Adding partitions to a Kafka topic changes the key-to-partition mapping for new messages, which breaks ordering for existing keys. It also does nothing for one dominant key.
- Dedicated lanes add operational cost and a list of "top tenants" that goes stale.
- Caches can serve stale data, and rate limits hurt the tenant that is growing fastest.
- A common mistake is adding consumers or brokers first. That does not fix a single hot key.

**How I'd monitor it**
- Per-partition bytes-in and message rate, and consumer lag per partition (for example with Kafka's `kafka-consumer-groups` tool or your metrics stack).
- Alert when the max partition rate divided by the median is above a chosen threshold, for example 3x.
- In Splunk, search logs by key and count per partition to find the top keys.
- In NoSQL stores, watch per-node CPU, per-partition read/write latency and throttling errors.
- Cache hit ratio, and rejected-request counts from the rate limiter.

**Follow-ups to expect**
- *Does adding partitions fix a hot key?* -> No. One key still hashes to one partition. It only helps if the problem is overall volume.
- *How do you keep order after salting?* -> Salt by a sub-key that has its own ordering need (like `orderId`), so order holds where it matters. Otherwise add a sequence number and reorder in the consumer.
- *How do you decide between a better key and a dedicated lane?* -> Change the key if the business does not need the old ordering. Use a dedicated lane when a few known tenants dominate and ordering must stay per tenant.

**60-second answer**
First I prove it is skew: per-partition rate and lag show one partition far above the rest. Then I find which key causes it. The best fix is a higher-cardinality partition key, such as order ID instead of tenant ID. If I still need tenant grouping, I add a salt or sub-key, but only where ordering across the pieces is not needed. For hot reads I add a local cache, and for abusive tenants I add rate limits. For the very biggest tenants I give them dedicated partitions or queues. I would not just add consumers or partitions, since that does not split one hot key. Then I alert on the ratio of max to median partition rate so I catch it early.

### Q14 [senior] Eventual consistency in the UI - how do you handle it?
tags: eventual-consistency, rest-api, ui-design, idempotency, read-your-writes, kafka, basics

**Start here: the concepts**
- **Eventual consistency:** after a write, different parts of the system may briefly show different data. Given no new writes, they all agree after a short time. It exists because making every copy update instantly (through queues, replicas, or separate services) costs speed and availability.
- **Read model / replica:** a copy of the data built for reading. It is updated a little after the main write, so it can be stale.
- **Primary (leader):** the copy that accepts writes and always holds the latest data. Replicas follow it with a delay.
- **HTTP 202 Accepted:** the server says "I received your request and will process it later," not "it's done."
- **Status endpoint:** a URL the client can check to see whether the work is pending, succeeded, or failed. The 202 response normally points to it in a `Location` header.
- **Optimistic UI update:** the screen shows the expected result immediately, before the server confirms. If the server later rejects the change, the UI rolls it back.
- **Read-your-writes:** a user who just made a change must see it, even if other users still see old data.
- **Version token:** a number or timestamp returned by a write. The client sends it with later reads, and the server only answers from a copy at least that new.
- **Idempotency key:** a unique ID sent with a request so that a repeated request is processed once.

**The live scenario**
An order service handles about 2,000 orders per minute at peak. `POST /orders` writes to the primary database and publishes an event. A consumer updates a search-backed "My Orders" read model. Normally this takes 1-2 seconds. During a Kafka consumer rebalance, the delay grew to about 40 seconds. Users clicked "Place order", landed on "My Orders", saw nothing, and clicked again. In this illustrative case, about 1.5% of orders were duplicated and support tickets spiked. The backend was behaving as designed. The UI pretended it was synchronous.

**What the interviewer is really checking**
Whether you treat eventual consistency as a user-experience and API-contract problem, not just a backend fact. They want to see honest states, protection against duplicates, and awareness of stale and out-of-order data.

**How I answer it**
1. **Return `202` with a status URL.** The API admits the work is asynchronous, and the client gets a way to ask "is it done?" For example: `202 Accepted`, `Location: /orders/42/status`.
2. **Show explicit "processing" states.** The UI shows "Order received, confirming..." and polls the status endpoint, or uses SSE or WebSocket, until it reaches a final state. Users do not resubmit when the screen tells them what is happening.
3. **Use optimistic updates only where failure is rare and reversible.** Add the item to the list immediately, mark it "pending", and roll back with a clear message if the server rejects it. Avoid this for money or stock decisions.
4. **Give the writer read-your-writes.** Either route that user's reads to the primary for a short window after their write (say 5-10 seconds), or return a version token and have reads wait for or require a copy at least that fresh. Others can stay on replicas, which keeps the primary lightly loaded.
5. **Make the UI tolerant of duplicates and reordering.** Events and responses can arrive twice or out of order. Key items by ID, and apply an update only if its version is newer than the one displayed. Send an idempotency key with every write so a double click or retry creates one order.
6. **Fail honestly.** If processing exceeds a time limit, show "taking longer than usual, we'll email you" rather than spinning forever.

**Trade-offs and what can go wrong**
- Reading from the primary protects users but adds load. A long window can defeat the purpose of having replicas.
- Optimistic UI feels fast but rollbacks confuse users if poorly explained.
- Polling costs requests: 10,000 users polling every second is 10,000 QPS. Use backoff, or push instead.
- Version tokens need infrastructure support. Replicas must be able to report how far they have caught up.
- Common mistake: a status endpoint that returns 404 until processing starts. Create the status record in the same transaction as the write.
- Common mistake: no idempotency key, so retries create duplicates.

**How I'd monitor it**
- Consumer lag and replica lag, with alerts on thresholds.
- p99 time from `202` to terminal status.
- Number of `GET` requests that return not-found right after a `POST`.
- Idempotency-key conflicts and duplicate-submission rate. Search these in Splunk by correlation ID.
- Status polling rate and "stuck pending" count older than N minutes.

**Follow-ups to expect**
- *Polling or push?* -> Polling is simple and robust. SSE or WebSocket cuts load at high scale but needs connection management. Start with polling plus backoff.
- *How do you stop double submits?* -> Disable the button, and send an idempotency key that the server stores, so a repeat returns the original result.
- *When should you avoid eventual consistency?* -> When a stale read causes real harm, such as checking a balance before a payment. Use a strongly consistent read for that step.

**60-second answer**
Eventual consistency means the UI can briefly show old data, so I design the experience around it. Writes return 202 with a status URL, and the UI shows "processing" until it reaches a final state. I use optimistic updates only for low-risk actions and roll back on failure. For the user who just wrote, I guarantee read-your-writes by reading from the primary for a short window or passing a version token. I make the UI tolerant of duplicates and reordering by using IDs, version checks and idempotency keys. I monitor consumer lag, time to completion, and duplicate rates.

### Q15 [architect] Design a notification service (email/SMS/push).
tags: system-design, notification-service, kafka, circuit-breaker, idempotency, retry, dlq, basics

**Start here: the concepts**
- **Event (`NotificationRequested`)**: a small message saying "someone needs to be notified about X". Producers (orders, payments, auth) publish it and move on, so they never wait for email or SMS providers.
- **Kafka topic**: a durable, ordered log that holds events until consumers read them. It absorbs traffic spikes so the slower downstream parts can catch up.
- **Router**: the stage that reads the event and decides who gets what, on which channel. It looks up the user's preferences and fills in a **template** (a message with placeholders such as name and order number).
- **Channel and provider**: email, SMS and push are channels. A provider is the external company that actually delivers: SES (email), Twilio (SMS), FCM (push). Providers are slow, rate-limited and sometimes down.
- **Per-channel queue and workers**: each channel gets its own queue and worker pool. A slow SMS provider then cannot block email.
- **Rate limit**: a cap on calls per second so we stay inside what the provider allows.
- **Circuit breaker**: after repeated failures it stops calling the provider for a while, so we do not pile up waiting threads, then probes to see if it recovered.
- **Retry with backoff**: retry failed sends after growing delays (1s, 5s, 30s...), ideally with random jitter. **DLQ (dead-letter queue)**: where messages go after retries run out, so people can inspect and replay them.
- **Dedupe / idempotency**: sending the same notification id twice has the effect of sending it once. This matters because Kafka and retries are at-least-once, meaning duplicates can happen.
- **Opt-out and quiet hours**: legal and trust rules. A user may refuse a channel or topic, or not want messages at night.

**The live scenario**
A shop sends about 20M notifications a day, roughly 230/s on average. A flash sale pushes 3M in 10 minutes, which is about 5,000/s. The SMS provider slows from 300 ms to 8 s. By Little's Law (in-flight = rate × latency), in-flight calls jump from about 1,500 to about 40,000. The worker threads are exhausted, login OTP codes queue behind marketing texts, and timeout retries cause some customers to get the same SMS three times.

**What the interviewer is really checking**
Whether you design for the failure of external providers (isolation, backpressure, idempotency) rather than drawing a happy-path pipeline, and whether you treat OTPs and marketing differently.

**How I answer it**
1. **Clarify requirements and numbers.** Channels, volume (average and peak: 230/s average, plan for about 10x peak), latency targets (OTP in seconds, marketing in minutes), and whether sends must be unique. These answers drive every later choice.
2. **Producers publish `NotificationRequested` to Kafka.** Use the outbox pattern on the producer side (write the event in the same database transaction as the business change, then relay it), so no event is lost. Kafka decouples producers and buffers spikes.
3. **Router resolves preferences and templates, and applies opt-out and quiet hours here, before anything is queued.** Filtering early means we never pay for or send a message we are not allowed to send. Quiet hours usually delay (reschedule) non-urgent messages, while critical ones such as OTPs bypass them.
4. **Publish to per-channel, per-priority queues.** Separate topics such as `sms-otp` and `sms-marketing` keep urgent traffic from waiting behind bulk traffic. Partition by user id to keep a user's messages in order.
5. **Workers call providers behind a circuit breaker and a per-provider rate limiter.** The limiter keeps us inside the provider's quota, and the breaker fails fast when the provider is sick. With a fallback provider configured, the breaker can switch to it. Set tight timeouts so a slow provider cannot hold threads.
6. **Dedupe by notification id.** Before sending, record the id with an atomic "insert if absent" in a store such as Redis or a database unique key. Duplicates are then skipped. Pass the id as the provider's idempotency key where supported. Without this, retries cause the triple SMS above.
7. **Store status.** Record states such as requested, sent, delivered, failed and suppressed. Providers report final delivery asynchronously by webhook, so update status from those callbacks too.
8. **Retry transient failures with backoff, then DLQ.** Retry timeouts and 5xx errors, but never permanent ones (invalid number, unsubscribed). After the limit, send to the DLQ and alert, with a tool to replay.

**Trade-offs and what can go wrong**
- Exactly-once delivery to a third party is impossible. We get at-least-once plus dedupe, and a rare duplicate or loss in a crash window remains.
- Retries without jitter and limits cause retry storms against a struggling provider.
- Too-aggressive breakers drop good traffic. Too-lenient ones exhaust threads.
- Delaying messages for quiet hours needs a scheduler, which adds complexity.
- A failover provider has different templates, sender reputation and cost.
- Storing every status at 5,000/s needs a store that can take that write rate.

**How I'd monitor it**
Delivery rate, end-to-end latency (p50/p99 from request to sent) and failure rate per provider and channel. Also Kafka consumer lag per queue, circuit breaker state changes, DLQ depth, dedupe-hit count and rate-limiter rejections. Alert on OTP latency, lag growth and DLQ growth. In Splunk, search by notification id to trace one message through all stages.

**Follow-ups to expect**
- *How do you guarantee OTPs are not delayed by a campaign?* -> Separate topics, worker pools and provider quotas per priority, so bulk traffic cannot starve urgent traffic.
- *A provider is fully down. What happens?* -> The breaker opens, messages wait in the queue or fail over to a backup provider, and consumer lag alerts fire. Nothing is lost because Kafka retains the events.
- *How do you dedupe across retries and consumer restarts?* -> A unique notification id, an atomic insert-if-absent with expiry, and the same id as the provider's idempotency key.

**60-second answer**
Producers publish a `NotificationRequested` event to Kafka, using an outbox so events are never lost. A router reads each event, loads the user's preferences and template, and drops anything the user opted out of, delaying non-urgent messages during quiet hours. It then puts the message on a separate queue per channel and priority, so OTPs never wait behind marketing. Workers call providers like SES, Twilio and FCM behind per-provider rate limits and circuit breakers, with short timeouts. Every notification has a unique id used for dedupe, because retries and Kafka are at-least-once. Transient failures retry with backoff and then go to a DLQ, and I store status, including provider webhooks. I watch delivery rate, latency and failures per provider, consumer lag and DLQ depth.

### Q16 [architect] Design a rate-limited API gateway for partners.
tags: api-gateway, rate-limiting, token-bucket, redis, kafka, system-design, basics

**Start here: the concepts**
- **API gateway:** a single front door that every partner request passes through. It handles auth, limits and logging once, so each backend service doesn't have to.
- **API key / OAuth2 client credentials:** two ways for a partner's *system* (not a person) to prove who it is. An API key is a secret string sent with each call. With client credentials, the partner swaps its ID and secret for a short-lived token, which is easier to expire and revoke.
- **Rate limit:** a cap on requests per second, so one partner can't overload the platform.
- **Token bucket:** each partner has a bucket that refills at a steady rate, for example 100 tokens per second, up to a maximum size. Each request takes one token. If the bucket is empty, the request is rejected. The bucket size allows short bursts while the refill rate enforces the average.
- **Quota:** a longer-term allowance by plan, such as 1M calls per month. It is separate from rate limiting, which protects the system, while quotas protect the business model.
- **Redis:** a very fast in-memory store. All gateway instances share it, so a partner's count is global rather than per server.
- **Lua script:** a small script Redis runs as one indivisible step. Without it, two gateways could both read "1 token left" and both spend it (a race condition).
- **429 and Retry-After:** HTTP 429 means "Too Many Requests". The `Retry-After` header tells the client how many seconds to wait.
- **Usage metering:** recording who called what, for billing. Kafka is a durable log, so metering can happen asynchronously without slowing the request.
- **Fail-open / fail-closed:** what to do when the limiter itself is down. Fail-open lets traffic through; fail-closed blocks it.

**The live scenario**
A payments platform has 50 partners and peaks at about 5,000 requests per second. One partner's retry loop goes wrong and sends 3,000 requests per second. Without limits, the shared backend slows down and every partner sees timeouts. With per-partner limits, only that partner receives 429s and everyone else is unaffected. Billing disputes also arise, because partners ask "how many calls did we make?" and the team needs an exact, auditable answer.

**What the interviewer is really checking**
Whether you separate protection (rate limit) from commercial limits (quota) and billing (metering), handle concurrency correctly, and decide deliberately what happens when a dependency fails.

**How I answer it**
1. **Authenticate first.** Validate the key or token at the gateway and resolve it to a partner ID and plan. Limits must be keyed on a verified identity, not an IP address, or they can be spoofed or shared by mistake.
2. **Apply a per-partner token bucket in Redis.** Key it by partner ID, with rate and burst taken from the plan. A token bucket is friendlier than a fixed window because it doesn't allow double bursts at window boundaries.
3. **Do the check in a Lua script.** Read tokens, refill based on elapsed time, deduct one and return allow or deny, all in one atomic step. This costs one network round trip, roughly 1 ms. If you run Redis Cluster, keep each partner's keys in the same hash slot.
4. **Check quotas per plan.** Keep daily and monthly counters with expiry (TTL) matching the period, and compare them to the plan's allowance. Check the cheap rate limit first.
5. **Reject clearly.** Return `429` with `Retry-After`. Use 401 or 403 for auth failures, so partners can tell "slow down" from "you're not allowed".
6. **Meter asynchronously.** After the response, publish a usage event (partner, endpoint, status, request ID) to Kafka, keyed by partner. A billing consumer aggregates the events. Kafka delivery is at-least-once, so billing deduplicates by request ID. Don't bill from Redis counters, because they are approximate and expire.
7. **Decide the Redis-down behaviour per route.** Fail-open for low-risk reads, so a limiter outage doesn't become a full outage. Fail-closed for abuse-sensitive or costly endpoints such as payments. A middle option is a coarse in-memory per-instance limit as a fallback. Set a short Redis timeout (tens of milliseconds) so a slow Redis doesn't stall requests.

**Trade-offs and what can go wrong**
- Redis is on the hot path of every request, so it needs replication and a timeout. A failover can lose a few recent counts, which is acceptable for limiting but not for billing.
- Fail-open risks abuse during an outage. Fail-closed risks self-inflicted downtime.
- A bucket per partner can be unfair inside a partner. Large partners may need per-endpoint buckets.
- Clients that retry immediately on 429 make things worse, so document backoff.
- Metering can lag or duplicate events, so reconcile billing against gateway logs.

**How I'd monitor it**
- Allowed versus 429 counts per partner, and gateway latency (p99) split into Redis time and total time.
- Redis errors, timeouts and fail-open/fail-closed activations. Alert on any fail-open event.
- Kafka consumer lag on the metering topic, and a daily reconciliation of billed calls against gateway logs.
- Splunk search for a partner's 429 spikes by partner ID. Alert when a partner reaches 80% of its quota.

**Follow-ups to expect**
- *Why not a fixed-window counter?* -> It is simpler, but it allows up to twice the limit around a window boundary. A token bucket smooths this and supports controlled bursts.
- *How do you scale Redis for this?* -> Shard by partner ID. At 5,000 requests per second, one node is enough, so scale for availability rather than throughput.
- *How do you avoid double billing?* -> Include a unique request ID in each event and make the billing consumer idempotent.

**60-second answer**
The gateway authenticates the partner with an API key or OAuth2 client credentials and maps it to a plan. It then runs a per-partner token bucket in Redis, using a Lua script so the check and the deduction are atomic across all gateway instances. Next it checks daily and monthly quotas for that plan. If a limit is hit, it returns 429 with a Retry-After header. Every call also emits a usage event to Kafka, and billing consumes those events asynchronously and deduplicates them. I'd add dashboards for 429s per partner, Redis latency and Kafka lag, with alerts on them. If Redis goes down, I decide per route: fail-open for low-risk reads, fail-closed for abuse-sensitive endpoints, and a short timeout so a slow Redis can't stall the gateway.

### Q17 [architect] Design a payment/wallet transfer system (strong correctness).
tags: payments, wallet, double-entry-ledger, idempotency, saga, outbox, consistency, basics

**Start here: the concepts**
- **Ledger:** an append-only record of money movements. You never edit history. You add new rows, so you can always explain how a balance came to be.
- **Double-entry:** every transfer writes at least two entries, a debit on one account and a credit on another, and they sum to zero. If the sum is not zero, you know something is broken.
- **Immutable entries:** entries are never updated or deleted. A mistake is fixed with a new reversing entry. This is what makes auditing possible.
- **Transaction (ACID):** a group of writes that all succeed or all fail. Debit and credit must never be half-done.
- **Shard:** one slice of a database split by key, such as account ID. A transaction is simple inside one shard and hard across shards.
- **Saga:** a multi-step workflow across services or shards. Each step has a compensating step (an undo), used when a later step fails.
- **Idempotency key:** a unique ID the client sends with a request. If the same key arrives again, the server returns the first result instead of moving money again.
- **Optimistic locking:** each balance row carries a version. An update says "apply only if the version is still N". If someone else changed it, you retry. **Serializable** isolation makes the database behave as if transactions ran one at a time, at the cost of aborts you must retry.
- **Outbox pattern:** write the event ("transfer completed") into an outbox table in the same transaction as the money change. A separate relay publishes it to Kafka later. This avoids "money moved but no event" or the reverse.
- **Reconciliation:** a scheduled job that compares our ledger with bank or partner statements and with downstream copies, and flags differences.
- **CP (consistency over availability):** during a network split, refuse requests rather than risk a wrong balance.

**The live scenario**
A wallet app handles 50M transfers/day, about 600/s on average and about 3,000/s at peak. Each transfer writes 2 ledger rows. A slow database made the mobile client time out at 3 seconds and retry. The first attempt had actually succeeded, so 0.1% of users (about 50k transfers/day) were debited twice. Support tickets spiked and finance could not explain the gap quickly. The fix was not faster hardware. It was idempotency, an immutable ledger and reconciliation.

**What the interviewer is really checking**
Whether you treat money as a correctness problem first. That means no lost or duplicated money under retries, crashes and partial failures, and being honest that "exactly-once" comes from design, not from the network.

**How I answer it**
1. **Clarify requirements.** Ask about currencies, peak QPS, whether transfers cross shards or services, and the latency target. Correctness comes before availability, so I pick CP. At 3,000 transfers/s the write volume is about 6,000 rows/s, which a sharded relational database handles.
2. **Model data as a double-entry ledger.** Entries are append-only and each transfer's entries sum to zero. A balance is either computed from the entries or kept as a cached row that is updated in the same transaction. The reason is that history is the source of truth and every balance is explainable.
3. **Execute the transfer atomically.** If both accounts live on the same shard, I use one database transaction. It checks the balance, writes the debit and credit, and writes the outbox row. If accounts sit on different shards or services, I use a saga: reserve or debit, then credit, with a compensating reversal if the credit fails. A single transaction cannot span shards without two-phase commit, which is slow and fragile, so I avoid it.
4. **Protect the balance check.** Use optimistic locking on the account version, or serializable isolation, so two concurrent debits cannot both pass the "enough funds" check. Retry on conflict.
5. **Make retries safe with idempotency keys.** Store the key with a unique constraint, in the same transaction as the ledger write. A replay hits the constraint and returns the stored result. The reason is that networks give at-least-once delivery, so the system must make duplicates harmless. That is how we get the effect of exactly-once.
6. **Publish events through the outbox.** The relay delivers at-least-once, so consumers must deduplicate by event ID.
7. **Reconcile and audit.** Run daily and intraday jobs comparing ledger totals, shard totals and partner statements. Keep an audit trail of who did what. Fix errors with reversing entries only.

```sql
UPDATE account SET balance = balance - :amt, version = version + 1
WHERE id = :id AND version = :v AND balance >= :amt;  -- 0 rows updated = retry or reject
```

**Trade-offs and what can go wrong**
- CP means some transfers are rejected during an outage. That is deliberate.
- Serializable and optimistic locking cause retries on hot accounts such as merchants. Consider batching or splitting those accounts.
- Sagas are only eventually consistent, so the intermediate state ("pending") must be visible, and compensations must be idempotent too.
- A common mistake is checking the idempotency key outside the money transaction, which leaves a race window.
- Another is updating or deleting ledger rows to "fix" data.

**How I'd monitor it**
- Reconciliation difference count and amount, which should be zero. Alert on any non-zero value.
- Sum of all ledger entries, which must be exactly zero.
- Duplicate-key hits (idempotent replays), transfer latency p99, and optimistic-lock retry rate.
- Saga transfers stuck in pending beyond a threshold.
- Outbox backlog age and Kafka consumer lag.
- Splunk searches by transfer ID and idempotency key to trace one transfer end to end.

**Follow-ups to expect**
- *Can you get exactly-once?* -> Not over a network. You get at-least-once delivery plus idempotent processing, so the effect happens once.
- *Why not two-phase commit across shards?* -> It blocks on coordinator failure and adds latency. A saga with compensation scales better, as long as each step is idempotent.
- *How do you handle a hot account?* -> Shard its balance into sub-balances, or queue and batch its updates, while keeping the ledger entries immutable.

**60-second answer**
I'd start by choosing consistency over availability, because wrong money is worse than a rejected request. The core is an immutable double-entry ledger, where each transfer writes a debit and a credit that sum to zero. Within one shard I do the balance check, both entries and an outbox row in a single database transaction, using optimistic locking or serializable isolation. Across shards or services I use a saga with compensating reversals. Every request carries an idempotency key with a unique constraint inside the same transaction, so client or network retries cannot double-debit. That gives the effect of exactly-once on top of at-least-once delivery. Events go out through the outbox, and reconciliation jobs and audit trails catch anything that still drifts.

### Q18 [architect] Design a real-time chat / notification push system (WebSocket/SSE).
tags: websocket, sse, chat-system, kafka, presence, cassandra, basics

**Start here: the concepts**
- **WebSocket**: one long-lived two-way connection between browser/app and server. The server can push a message at any moment without the client asking. Plain HTTP can't do this.
- **SSE (Server-Sent Events)**: a simpler one-way server-to-client stream over HTTP. It auto-reconnects and suits notifications. Use WebSocket when the client also sends often (chat).
- **Gateway layer**: stateless-looking servers whose only job is to hold these connections. Each connection lives on exactly one node, so the node is "sticky" for that connection's lifetime.
- **Presence registry**: a fast lookup of "which user is online, on which gateway node". Redis suits it, with a TTL refreshed by heartbeats so crashed nodes expire on their own.
- **Kafka topic keyed by conversation**: messages with the same key go to the same partition, so order within a conversation is preserved. Kafka stores messages durably.
- **Redis pub/sub**: fire-and-forget broadcast. If nobody is listening at that moment, the message is gone.
- **Wide-column store (Cassandra/Couchbase)**: scales writes horizontally. Data is grouped by conversation and sorted by time.
- **Offline push**: when the user has no connection, the mobile OS push services (APNs/FCM) deliver the alert.
- **Last-seen id**: the id of the last message the client received. On reconnect it asks "give me everything after this".

**The live scenario**
A chat app has 2M concurrent connections and 20k messages/s at peak. One gateway node comfortably holds about 50k connections, so we need 40 nodes and run 60 for headroom. During a rolling deploy, 50k clients reconnected at once. Users saw missing messages and duplicates, because messages sent during the gap were never replayed.

**What the interviewer is really checking**
Whether you separate connection handling from message flow, and whether you handle ordering, durability, and failure (reconnect, offline users). Also whether you know which tools are durable and which are not.

**How I answer it**
1. **Clarify**: 1:1 or group chat, maximum group size, delivery guarantee, ordering needs, message retention. I assume at-least-once delivery with ordering per conversation.
2. **Gateway nodes** hold the WebSockets. I size them by connections per node (2M / 50k = 40, plus headroom). The connection is sticky to one node, but the load balancer needs no special affinity. Any node can accept a new connection.
3. **Presence in Redis**: user id → gateway node id, with a TTL refreshed by heartbeats. Without this, we couldn't route a message to the right node.
4. **Send path**: the gateway writes the message to Kafka with the conversation id as key. Partitions give parallelism, and the key gives order within a conversation. Consumers then do two jobs:
   - Persist the message.
   - Look up recipients in presence and forward to their gateway node.
5. **Persistence**: store in Cassandra/Couchbase with partition key = conversation id (plus a time bucket, so busy rooms don't create giant partitions) and clustering by time-ordered message id. This makes "latest N messages" and "everything after id X" cheap range reads.
6. **Offline users**: if presence has no entry, send a push notification through APNs/FCM. The message is already stored, so they fetch it on next open.
7. **Reconnect without gaps**: the client sends its last-seen id. The server replays newer messages from the store. The client dedups by message id, which makes at-least-once delivery safe.
8. **Redis pub/sub only for the last hop** (consumer → gateway node), never as the source of truth, because it is not durable. This corrects the idea of using it interchangeably with Kafka.

**Trade-offs and what can go wrong**
- **Reconnect storms**: add jittered backoff on clients and rate-limit connection accepts.
- **Hot conversations**: a huge group means fan-out cost. Fan out in consumers and cap group size or batch.
- **Stale presence**: a message may go to a dead node. The replay on reconnect covers this.
- **Ordering** is per conversation only, not global.
- **Exactly-once** is not achievable end to end. Use at-least-once plus client dedup.
- **Large Cassandra partitions** hurt performance, hence time bucketing.

**How I'd monitor it**
- Connections per node and connect/disconnect rate.
- End-to-end latency (send → delivered), p99.
- Kafka consumer lag per partition.
- Replay volume after reconnect.
- Push failure rate.
- Splunk search on message id to trace one message across gateway, consumer, and store.
- Alerts on lag growth and on sudden disconnect spikes.

**Follow-ups to expect**
- *How do you scale beyond one Kafka partition's throughput?* -> Add partitions. Order stays per conversation key, but changing the partition count remaps keys, so plan it early.
- *WebSocket or SSE?* -> SSE for one-way notifications (simpler, auto-reconnect). WebSocket for chat's bidirectional traffic.
- *How do you handle a gateway node crash?* -> Presence TTL expires, clients reconnect to other nodes, and they replay from last-seen id.

**60-second answer**
I'd put WebSocket gateway nodes in front, sized by connections per node. Each connection lives on one node, and Redis presence with a heartbeat TTL maps a user to that node. Messages go to Kafka keyed by conversation id, so order is kept per conversation. Consumers persist them in Cassandra or Couchbase, partitioned by conversation and sorted by time, then forward to the recipient's gateway. Offline users get an APNs/FCM push. On reconnect the client sends its last-seen id and we replay the gap, with client-side dedup for at-least-once delivery. Redis pub/sub is only a fast last hop because it isn't durable. I'd monitor connections, p99 latency, and Kafka lag.

### Q19 [architect] Design a distributed job scheduler (run a cron job once across 10 pods).
tags: system-design, job-scheduler, leader-election, distributed-lock, idempotency, kubernetes, basics

**Start here: the concepts**
- **Cron job:** a task that runs on a schedule, such as "every night at 02:00". On one server it is simple. With 10 identical pods, every pod's timer fires, so the task runs 10 times.
- **Pod:** one running copy of your service in Kubernetes. All 10 copies run the same code and the same schedule.
- **Leader election:** the pods agree on one "leader", and only the leader runs scheduled work. Kubernetes offers a **Lease**, a small shared record with an owner and an expiry time. The leader keeps renewing it. If the leader dies, the lease expires and another pod takes over.
- **Database lock:** the database is the referee. `SELECT ... FOR UPDATE` locks a row so others must wait. `SKIP LOCKED` makes others skip locked rows instead of waiting, so each pod claims a different job row.
- **ShedLock:** a small Java library for Spring `@Scheduled` methods. Before running, a pod writes a lock row in a shared store (database, Redis and others). If the row is already held, the pod skips that run. It is only a lock, not a scheduler.
- **Quartz cluster mode:** Quartz is a full scheduler library. In cluster mode it keeps its jobs and triggers in shared database tables, so only one node fires each trigger.
- **Kubernetes CronJob:** Kubernetes itself starts a fresh pod on schedule, runs the task and exits. Your 10 service pods are not involved.
- **Idempotent:** running the same job twice gives the same result as running it once. It is your safety net when the "only once" guarantee fails.
- **Heartbeat / timeout:** a running job updates a timestamp every few seconds. If the timestamp goes stale, the job is presumed dead and can be taken over.

**The live scenario**
A billing service runs on 10 pods. At 02:00 a `@Scheduled` job sends invoices to 200,000 customers. After a scale-out from 3 to 10 pods, customers received duplicate invoices, because every pod fired the job. The team added a lock, but one pod crashed mid-run with the lock held, so the next night's run was blocked. Nobody noticed for two days because no alert existed for missed runs.

**What the interviewer is really checking**
Whether you know that "exactly once" is not achievable. You get at most one *attempt* at a time, plus idempotent work and crash recovery. They also want to see that you pick a tool based on the failure modes, not by name.

**How I answer it**
1. **Clarify requirements.** How many jobs, how long they run, and how bad a duplicate or a missed run is. Also whether I already have a database. This decides how heavy the solution should be.
2. **Pick the mechanism by need.**
   - For a few simple jobs in a Spring app, use **ShedLock**. It is the cheapest option and uses the database I already have.
   - For many jobs, persistence, misfire handling and calendars, use **Quartz in cluster mode**. It needs the JDBC job store and synchronised clocks.
   - For heavy, isolated or long jobs, use a **Kubernetes CronJob** with `concurrencyPolicy: Forbid`. It has separate resources and no coupling to the service pods. Kubernetes documents that a schedule can occasionally create two runs or none, so it still needs idempotency.
   - Use **leader election** (Kubernetes Lease) when one pod should own all scheduling.
   - Use **`FOR UPDATE SKIP LOCKED`** to spread many job rows across pods like a work queue. Do not hold the transaction open for the whole job. Instead, claim the row by setting owner and lease expiry, then commit.
3. **Make the job idempotent.** A lock can be lost, for example when a pod pauses during a long garbage collection and the lease expires. A natural key makes the second run harmless:
   ```sql
   INSERT INTO job_run(job, slot) VALUES ('invoices','2024-05-01T02:00')
   ON CONFLICT DO NOTHING;  -- 0 rows inserted = someone else has it
   ```
4. **Record runs and status.** Keep a table with start, end, owner and status (RUNNING, OK, FAILED). This gives you an audit trail and lets you find stuck runs.
5. **Add timeouts and a heartbeat.** The owner renews a lease while working. If the heartbeat goes stale, another pod takes over. Without this, one crash blocks the job forever, which is what happened in the scenario.
6. **Alert on missed runs.** Alert when no success has been recorded within the expected window.

**Trade-offs and what can go wrong**
- Leader election gives a single point of throughput. Failover takes up to the lease duration.
- A lease that is too short causes double runs. One that is too long causes slow recovery.
- ShedLock's `lockAtMostFor` that is too small lets a second pod start while the first is still running. Too large delays recovery after a crash.
- Different pod clocks break time-based locks.
- A CronJob adds pod start-up time, and skipped runs happen if the cluster is down.
- Holding a database transaction open for a whole job exhausts connections.

**How I'd monitor it**
- Use a "last successful run" timestamp per job and alert when it is older than the schedule plus a grace period.
- Track job duration and failure count.
- Count runs that were skipped by the lock, and count takeovers after a stale heartbeat.
- In Splunk, search by job name and slot, and alert when more than one `STARTED` event shares the same slot (a duplicate run). Alert also when a slot has no `COMPLETED` event.

**Follow-ups to expect**
- *Why can't you guarantee exactly once?* -> A pod can finish the work and crash before recording success, so the system cannot tell whether the run happened. Aim for at-least-once plus idempotency.
- *What is a fencing token?* -> A number that increases with each lock grant. The resource rejects writes carrying an older number, which stops a paused ex-leader from doing damage.
- *How do you scale to thousands of jobs?* -> Store jobs as rows and let pods claim due rows with `SKIP LOCKED` and a lease, or partition jobs by key.

**60-second answer**
Ten pods means ten timers, so I need a single owner for each run. For a few jobs I use ShedLock on the existing database. For many jobs I use Quartz in cluster mode, and for heavy isolated work a Kubernetes CronJob with Forbid concurrency. Locks can still fail through crashes or long pauses, so every job must be idempotent, for example with a unique key per job and time slot. I record each run's status, and the owner sends a heartbeat so another pod can take over from a dead one. Finally, I alert when a job has no successful run in its expected window, because a silent missed run is the real production risk.

### Q20 [architect] How do you design for zero-downtime deployments including database changes?
tags: zero-downtime, deployment, expand-contract, schema-migration, canary, feature-flags, basics

**Start here: the concepts**
- **Zero-downtime deployment:** users never see errors or pauses while new code goes live. It matters because during a release old and new versions run side by side, even if only for minutes.
- **Backward compatibility:** a change that doesn't break the previous version. New code must work with the old schema and old callers, and old code must work with the new schema.
- **Expand/contract (parallel change):** change a schema in three phases. *Expand* by adding the new thing alongside the old. *Migrate* by moving code and data over. *Contract* by removing the old thing once nothing uses it.
- **Rolling deploy:** replace instances a few at a time, so old and new run together.
- **Canary deploy:** send a small share of traffic (say 5%) to the new version first and watch it before going wider.
- **Readiness gate (probe):** a check that tells the load balancer when an instance can take traffic. A new instance gets no requests until it passes.
- **Feature flag:** a runtime switch that turns behaviour on or off without a deploy. It separates *deploying* code from *releasing* the feature.
- **Graceful shutdown:** an instance being stopped finishes in-flight work and stops taking new work, instead of dropping requests.
- **Versioned events:** messages (e.g. on Kafka) carry a schema version. Producers and consumers upgrade at different times, so both must tolerate the other's version.
- **SLO (service level objective):** a target such as "99.9% of requests succeed under 300 ms". An SLO regression means the new version is breaking that target.

**The live scenario**
An orders service runs 12 pods at about 2,000 req/s. A team renamed a column from `customer_phone` to `phone` and shipped the migration and the new code in one rolling deploy. For about 4 minutes the old pods queried a column that no longer existed. That is roughly 2,000 × 240 ≈ 480,000 failed requests, and rolling back the code did not help because the column was already gone. The fix was to stop treating schema and code as one atomic change.

**What the interviewer is really checking**
Whether you understand that during any deploy two versions run at once, and whether you can sequence database, code, and event changes so each step is safe and reversible.

**How I answer it**
1. **Assume old and new coexist.** Every API, schema, and event change must be compatible with the previous version. This is the root rule, and everything below follows from it.
2. **Expand first, in its own release.** Add the new nullable `phone` column and leave the old one alone. Old code ignores it, so nothing breaks. Use online, non-blocking DDL, since long table locks are themselves downtime.
3. **Ship code that handles both.** It writes both columns and reads the new one, falling back to the old. Backfill existing rows in small batches so the database isn't overloaded.
4. **Never ship a code change that *requires* a schema change in the same step.** Schema first, code later, contract last. Each step is then independently deployable and reversible.
5. **Roll out gradually with readiness gates.** Use a canary or rolling deploy. New pods get traffic only after passing readiness, and the rollout pauses if the canary looks bad.
6. **Shut down gracefully.** On SIGTERM, fail readiness, drain in-flight requests, and finish within the termination grace period. Kafka consumers should commit offsets and leave the group cleanly, so rebalances stay short.
7. **Hide risky behaviour behind feature flags.** Turning a feature off in seconds is faster and safer than redeploying.
8. **Version events.** Only add optional fields. Consumers ignore unknown fields, and an old event version stays supported until every consumer has upgraded.
9. **Contract last.** Drop the old column only after no old version runs and the rollback window has passed.
10. **Automate rollback.** If error rate or latency breaches the SLO during the canary, the pipeline reverts automatically. Rollback is safe because the schema only expanded.

**Trade-offs and what can go wrong**
- It takes more releases and more temporary code (dual writes, fallbacks) that must be cleaned up. Forgotten contracts leave schema debt.
- Dual writes can drift. Verify with a reconciliation query before contracting.
- Backfills on big tables can hurt production, so throttle them.
- Some changes (type changes, adding constraints) are harder to make backward-compatible and need extra phases.
- Rolling back data is hard, so only the code rolls back. That is why the expand step must be additive.
- Graceful shutdown fails if the grace period is shorter than the longest request.

**How I'd monitor it**
- Compare canary and baseline error rate, p99 latency, and saturation, and gate promotion on them.
- Watch the 5xx count and readiness flapping during the rollout.
- Track Kafka consumer lag and rebalance count during deploys.
- Check database lock waits and replication lag during migrations.
- In Splunk, search errors by `app_version` and watch for "column not found" or deserialization errors.
- Alert on any SLO burn during a deploy window.

**Follow-ups to expect**
- *How do you roll back after a schema change?* -> Roll back only the code. The expand step was additive, so old code still works. Never roll back by dropping the new column.
- *Blue/green or rolling?* -> Blue/green gives instant switch-back but doubles capacity, and both sides still share one database, so expand/contract is needed either way.
- *How do you migrate a huge table safely?* -> Add nullable columns, backfill in throttled batches, validate, then switch reads. Avoid locking DDL.

**60-second answer**
Zero downtime starts from one fact: during a deploy, old and new versions run together. So every change to the API, schema, or events must be backward compatible. For the database I use expand/contract. I add the new column first, ship code that handles both, backfill, and drop the old column much later. I never release a schema change and the code that depends on it together. I roll out with canary or rolling deploys gated by readiness probes. Instances shut down gracefully, and feature flags let me switch behaviour off instantly. Events are versioned so consumers upgrade independently. The pipeline watches SLOs and rolls back automatically, and rollback is safe because the schema only expanded.

### Q21 [mid] What is the difference between horizontal and vertical scaling and the limit of each?
tags: scaling, horizontal-scaling, vertical-scaling, stateless, sharding, replication, system-design, basics

**Start here: the concepts**
- **Scaling:** making a system handle more load (requests per second, data size) while staying fast. It exists because one machine eventually runs out of CPU, memory, disk or network.
- **Vertical scaling (scale up):** keep one machine but give it more CPU, RAM or faster disks. The application usually needs no code change.
- **Horizontal scaling (scale out):** add more machines and share the work between them.
- **Load balancer:** a component that spreads incoming requests across several identical servers.
- **Stateless service:** a server that keeps nothing between requests, because session and data live elsewhere (database, cache). Any instance can answer any request, so you can add or remove instances freely.
- **Stateful tier (a database, for example):** it holds data that must stay correct. You cannot just clone it, because the copies would drift apart.
- **Partitioning (sharding):** splitting data across machines, for example customers A-M on one node and N-Z on another, so each holds only part of it.
- **Replication:** keeping copies of the same data on several machines for read capacity and failover.
- **Consistency:** whether every reader sees the latest write. With copies, a replica may briefly return old data (replication lag).
- **Single point of failure (SPOF):** one component whose failure takes the whole system down.

**The live scenario**
An order service ran on one 8-core VM at about 200 requests per second (QPS). On a sale day traffic hit 2,000 QPS. CPU reached 95% and p99 latency (the time within which 99% of requests finish) went from 120 ms to 3 s. The first fix was a 32-core VM, which worked for a month. Then a bigger campaign came, the largest size on offer was already in use, and a resize needed downtime. The team moved to 6 identical instances behind a load balancer, and the API tier scaled well. Then the single primary database hit 90% CPU on writes. Adding instances had only moved the bottleneck.

**What the interviewer is really checking**
Whether you know that stateless tiers scale out easily while state is the hard part, and whether you can name where each approach stops working instead of calling one "better".

**How I answer it**
1. **Define both in one line each.** Vertical means a bigger machine and horizontal means more machines. Clear definitions show you are not mixing them up.
2. **Start with vertical's strengths.** It is the simplest option: no code change, no distributed-system problems, and transactions stay on one node. For a small or early system it is often the right first move.
3. **State vertical's limits.** There is a hard cap (the biggest machine available), cost rises faster than capacity, and resizing often needs a restart. It is also a single point of failure: if that box dies, everything is down.
4. **Explain horizontal for stateless tiers.** Put instances behind a load balancer and capacity grows close to linearly. Use Little's Law (concurrent requests = QPS x latency): 2,000 QPS x 0.1 s = 200 in flight. If one instance handles about 50, you need 4, so run 6 for headroom. Losing one instance also no longer causes an outage.
5. **Explain horizontal for state.** Data cannot simply be cloned. You need partitioning to spread writes and replication to spread reads and survive failures. That brings consistency problems such as stale reads from lagging replicas, and operational complexity.
6. **Close with the decision.** Scale up first while it is cheap and simple, design the application stateless so it can scale out, and plan partitioning before the data tier forces it.

**Trade-offs and what can go wrong**
- Vertical: downtime to resize, the ceiling, and a large blast radius if the machine fails.
- Horizontal: more moving parts (load balancing, deployment, network calls), and uneven load if some instances get more traffic.
- A shared database, cache or lock can cap the gains however many app servers you add.
- A common mistake is keeping user sessions in server memory, which makes the tier stateful and breaks scale-out.
- A poor shard key creates a "hot" partition that takes most of the traffic.

**How I'd monitor it**
- CPU, memory and p99 latency per instance, to spot saturation and skew between instances.
- Requests per second per instance and load balancer error rates.
- Database CPU, connection pool usage, and replication lag.
- Per-shard throughput, to catch hot partitions.
- In Splunk, search latency and errors grouped by host to see whether one node is the outlier.
- Alert when CPU stays above about 70% for several minutes, so you scale before users notice.

**Follow-ups to expect**
- *Why is horizontal scaling only "near-linear"?* -> Shared resources (database, locks, load balancer) and coordination overhead mean each extra node adds slightly less than the one before.
- *How do you make a service stateless?* -> Move sessions and data to a shared store (database, cache or token), so any instance can serve any request.
- *When would you pick vertical scaling today?* -> For a small system, a database that is hard to shard, or as a quick first step while you design the scale-out.

**60-second answer**
Vertical scaling means making one machine bigger. It is the simplest option because the code does not change, but it has a hard ceiling, costs rise steeply, and that one machine is a single point of failure. Horizontal scaling means adding more machines behind a load balancer. It scales almost linearly for stateless services, and losing one instance does not cause an outage. State is the hard part: databases need partitioning and replication, which bring consistency problems like stale reads. In practice I scale up first while it is cheap, design the services stateless, and scale out the app tier. Then I plan sharding and replication before the database becomes the bottleneck.

### Q22 [mid] Back-of-envelope estimation - show the method.
tags: back-of-envelope, capacity-planning, qps, storage, bandwidth, little's-law, basics

**Start here: the concepts**
- **Back-of-envelope estimation:** A quick calculation with round numbers, done before design, to learn the *size* of the problem (thousands of requests per second or millions?). It exists because the design for 100 RPS is very different from the design for 100,000 RPS, and you want to know which one you are building before you draw boxes.
- **DAU (daily active users):** The number of distinct users who use the product on a given day.
- **RPS / QPS (requests or queries per second):** How many requests hit the system each second. Servers and databases are sized in this unit, not in "per day".
- **Average vs peak:** Traffic is not flat. Peak is the busiest moment, and you must size for peak, not average. A multiplier such as x4 is a common assumption when you have no real data.
- **Storage estimate:** Size per record x number of records x time period.
- **Bandwidth:** Data moved per second, which is RPS x average payload size. It tells you whether the network is a bottleneck.
- **Headroom:** Spare capacity kept free for spikes, failures and deployments. Running nodes at 100% is unsafe.
- **Little's Law:** Requests in flight = arrival rate x time each takes. It tells you how many requests are being handled at once, which drives thread pools and connection pools.

**The live scenario**
A team was launching a feed feature. Product said "10 million daily users, about 20 requests each". An engineer said "a few servers will do." Doing the arithmetic showed a different picture: 200M requests/day is about 2,300 RPS on average and about 10k RPS at peak. Each request returned roughly 5 KB, so peak bandwidth was about 50 MB/s. Their first load test used 3 nodes and fell over at around 3k RPS. The estimate took five minutes and would have caught this before the launch date was fixed. (All numbers here are illustrative.)

**What the interviewer is really checking**
Whether you have a repeatable method: state assumptions, calculate in clear steps, and sanity-check the result. They are not checking exact numbers. They also want to see that you turn the numbers into a decision, such as node count or database choice.

**How I answer it**
1. **Clarify and state assumptions out loud.** "10M DAU, 20 requests per user per day, 1 KB per record." Reason: the interviewer can correct an assumption early, and the numbers are only as good as these inputs.
2. **Compute average QPS.** 10M x 20 = 200M requests/day. A day has 86,400 seconds (about 100k for a quick mental shortcut). 200M / 86,400 is about 2,300 RPS. Reason: the per-second figure is what you size servers against.
3. **Apply a peak factor.** 2,300 x 4 is about 10k RPS. Reason: you must survive the busiest moment, and averages hide it.
4. **Estimate storage.** 100M new records/year x 1 KB = 100 GB/year. Then multiply for replicas (often 3x), indexes and overhead, and for the retention period. Reason: raw data size is only part of what the disks actually hold.
5. **Estimate bandwidth.** Peak RPS x payload size. 10k x 5 KB = 50 MB/s, about 400 Mbit/s. Reason: this shows whether network links or load balancers become the limit.
6. **Derive node counts with headroom.** If one node handles about 1,000 RPS in a load test, 10k RPS needs 10 nodes. Target about 50% utilisation, so about 20 nodes, spread across zones. Reason: a node or zone will fail, and traffic will exceed your guess.
7. **Use Little's Law for concurrency.** 10,000 RPS x 0.05 s latency = about 500 requests in flight. Reason: this sizes thread and connection pools.
8. **Sanity-check and state the next step.** Ask whether the result is plausible. Then say the numbers will be replaced by measurements once real traffic exists.

**Trade-offs and what can go wrong**
- Wrong assumptions multiply through every step. A 2x error in payload size becomes a 2x error in bandwidth.
- A fixed x4 peak factor can be wrong. Events like sales or a push notification can spike 20x.
- Over-provisioning wastes money, while under-provisioning causes outages. Autoscaling can ease this but does not remove the need to estimate.
- Forgetting replication, indexes and growth makes storage estimates too low.
- Spending ten minutes on exact arithmetic: round aggressively instead.

**How I'd monitor it**
Compare the estimate with reality. Track actual RPS (average and p99 peak), payload sizes, CPU per node, disk growth per week and network throughput. In Splunk, a search of request counts per minute grouped by endpoint shows real peak-to-average ratios. Alert when utilisation passes the headroom target, for example CPU above 60% sustained or disk above 70%. Then update the assumptions.

**Follow-ups to expect**
- *Why x4 for peak?* -> It is a rule-of-thumb assumption. Replace it with the real peak-to-average ratio from production metrics when you have them.
- *How do you know one node handles 1,000 RPS?* -> You measure it with a load test. Without one, state it as an assumption and flag it as the biggest risk.
- *What changes if reads are 100x more than writes?* -> Size reads and writes separately. Add caching and read replicas for reads, and size the write path and storage on the write numbers.

**60-second answer**
"I start by stating assumptions: say 10M daily users, 20 requests each, 1 KB per record. That gives 200M requests a day. Divide by about 86,400 seconds and I get roughly 2,300 requests per second on average. I multiply by about 4 for peak, so around 10k RPS. For storage, 100M new records a year at 1 KB is about 100 GB a year, and I would multiply for replicas and indexes. Bandwidth is peak RPS times payload size. Then I turn it into nodes: if one node handles 1,000 RPS, I need 10, and I double that for headroom and failures. The method matters more than the exact numbers, and I would replace the assumptions with real measurements once I have them."

### Q23 [fresher] Explain the SOLID principles with one example each.
tags: solid, oop, design-principles, dependency-injection, spring, clean-code, basics

**Start here: the concepts**
- **Class and interface:** a class is a blueprint holding data and behaviour. An interface is a promise of "what can be done" without saying how.
- **Reason to change:** a business need that forces you to edit the code, such as a new tax rule or a new print format.
- **Subtype / base type:** if `Square` extends `Rectangle`, then `Square` is the subtype and `Rectangle` is the base type.
- **Abstraction:** depending on an interface instead of a concrete class, so the actual implementation can be swapped.
- **Dependency injection (DI):** a class does not create the objects it needs. They are handed to it from outside, for example by Spring. DI is a technique. The Dependency Inversion Principle is the rule that DI helps you follow.
- **Why SOLID exists:** code changes constantly. These five habits keep a change in one place from breaking five others.

**The live scenario**
A billing service has one 2,000-line `InvoiceService`. It calculates totals, applies discounts with a long `if/else` chain, and prints PDFs. Each new discount rule means editing that class. Over a quarter, a "small" discount change breaks PDF printing twice, and about 3 hours of production invoicing is affected each time. The team splits the class along SOLID lines. After that, a new discount is a new small class, and the printing code is never touched.

**What the interviewer is really checking**
Whether you understand the *purpose* of each principle, which is to make change safe, and can give a small real example of each. Reciting the five names is not enough.

**How I answer it**
1. **S, Single Responsibility:** a class should have one reason to change. Keep `InvoiceCalculator` (maths) separate from `InvoicePrinter` (formatting). *Why:* a change to the PDF layout then cannot break the totals.
2. **O, Open/Closed:** add behaviour by adding code, not by editing tested code. Each discount becomes its own class behind one interface, so Black Friday means adding `BlackFridayDiscount` and changing nothing else.
   ```java
   interface DiscountStrategy { BigDecimal apply(BigDecimal total); }
   ```
3. **L, Liskov Substitution:** code written for the base type must work correctly with any subtype. A `Square` whose `setWidth` also changes the height breaks code that expects a `Rectangle` to keep its height. *Why:* if subtypes surprise callers, you end up with `instanceof` checks everywhere.
4. **I, Interface Segregation:** prefer small interfaces made for each client over one fat interface. An `OrderReader` with only `findById` suits a reporting module. A single giant `OrderRepository` forces it to depend on methods it never uses. *Why:* clients are not affected by changes to methods they don't call.
5. **D, Dependency Inversion:** high-level logic depends on abstractions, not concrete classes. `InvoiceService` receives a `DiscountStrategy` through its constructor, and Spring injects the real one. *Why:* you can swap implementations and pass a fake in unit tests.

**Trade-offs and what can go wrong**
- Over-applying SOLID gives dozens of tiny classes and interfaces with a single implementation. That is harder to read, not easier.
- "One responsibility" is a judgement call. Ask "who would ask me to change this?" rather than "does it have only one method?"
- Subclasses that throw `UnsupportedOperationException` for inherited methods are a typical Liskov violation.
- DI and the Dependency Inversion Principle are different things. You can use Spring and still depend on concrete classes.

**How I'd monitor it**
Design quality is not a runtime metric, so I use proxies:
- Static analysis (for example SonarQube): class size, cyclomatic complexity and duplication.
- Review history: how many files one feature change touches, and how often the same class is edited.
- Regression bugs per release.
- Unit-test ease: if a class needs a database to be tested, it probably violates D.

**Follow-ups to expect**
- *Which principle do you use most day to day?* -> D and S. Constructor injection and small focused classes make code testable.
- *How is DI different from the Dependency Inversion Principle?* -> DI is the technique of passing dependencies in. The principle says to depend on abstractions. DI helps you achieve it.
- *Can SOLID be overdone?* -> Yes. Add an interface when there is a real second implementation or a test need, not "just in case".

**60-second answer**
SOLID is five habits that make code safe to change. Single Responsibility means a class has one reason to change, so I keep the invoice calculator separate from the invoice printer. Open/Closed means I add new behaviour, like a new discount strategy class, without editing tested code. Liskov Substitution means a subtype must work wherever its base type is used, and a `Square` that breaks `Rectangle`'s setters violates that. Interface Segregation means small, client-specific interfaces instead of one fat one. Dependency Inversion means depending on abstractions and injecting the implementations, which Spring DI makes easy and also makes testing simple. I apply them with judgement so I don't create needless classes.

### Q24 [fresher] Which design patterns do you use most in Java/Spring?
tags: design-patterns, spring, strategy, proxy, template-method, factory, basics

**Start here: the concepts**
- **Design pattern**: a named, proven way to solve a problem that keeps coming up in code. Its value is a shared vocabulary: "use a Strategy here" tells a teammate the whole idea in one sentence.
- **Strategy**: several interchangeable ways to do one job (for example, parse a document), each in its own class behind one interface. The caller picks one at runtime, so it needs no big `if/else`.
- **Factory / Abstract Factory**: a factory is a method or class that creates objects so callers don't use `new` directly. An abstract factory creates a whole family of related objects.
- **Builder**: builds an object with many optional fields step by step (`.name(..).timeout(..).build()`), which is more readable than a constructor with 8 arguments.
- **Singleton**: one shared instance. In Spring, a bean is by default one instance per application context. This is not the textbook Singleton (private constructor, static access); the container just creates it once.
- **Template Method**: a fixed skeleton of steps where you fill in only the varying part. `JdbcTemplate` opens the connection, runs your SQL, maps rows, handles exceptions and closes resources. You supply only the SQL and the row mapping.
- **Proxy / Decorator**: a wrapper object with the same interface as the original that adds behaviour before or after calls. Spring AOP (`@Transactional`, `@Cacheable`) works by wrapping your bean in a proxy. Strictly this is Proxy; Decorator is the close cousin where you stack extra behaviour.
- **Observer**: one part publishes an event and any number of listeners react, without the publisher knowing them. In Spring: `ApplicationEventPublisher` and `@EventListener`.
- **Adapter**: converts one interface into the one your code expects. It is used to wrap a vendor's API so the vendor's types don't spread through your code.
- **Chain of Responsibility**: a request passes through a line of handlers, and each one can act, pass it on or stop it. Servlet filters and the Spring Security filter chain work this way.

**The live scenario**
A document service ingested filings from about 40 courts, each with its own format. One 1,500-line `if (court.equals("X"))` method handled all of them. Adding a court took about 3 days, and roughly 1 in 5 changes broke another court's parsing. The team moved to Strategy: one `CourtParser` per court, and Spring injected all of them as a map keyed by court code. A new court became one new class, taking about half a day, with its own tests. Old courts were never touched.

**What the interviewer is really checking**
Whether you know patterns as solutions to real problems you have met, not as a memorised list, and whether you can say honestly where Spring already applies them for you.

**How I answer it**
1. **Group them by problem.** Varying behaviour (Strategy, Template Method), creating objects (Factory, Builder, Singleton), wrapping behaviour (Proxy/Decorator, Adapter, Chain), reacting to things (Observer). Groups are easier to remember and show understanding.
2. **Give one project example per pattern you name.** Claiming a pattern with no example invites a probe you can't answer. The court parsers are my Strategy example.
3. **Point out where Spring does it for you.** Singleton beans, `JdbcTemplate`, AOP proxies, `@EventListener` and the security filter chain are all patterns I use daily without writing them.
4. **Show the shape in code.**
```java
interface CourtParser { ParsedCase parse(String raw); }
// Spring injects: Map<String, CourtParser> parsers (bean name = court code)
```
5. **State the reason, not just the name.** Strategy replaces `if/else`, Adapter keeps vendor changes in one class, and Builder avoids long constructors.

**Trade-offs and what can go wrong**
- Over-engineering: a pattern for two cases that never grow adds classes and no value.
- Spring singleton beans are shared across threads, so keep mutable state out of them.
- Proxy pitfall: calling a `@Transactional` method from another method in the same class bypasses the proxy, so the transaction doesn't apply.
- `@EventListener` runs synchronously on the publisher's thread by default, so a slow listener slows the publisher, and a failing one can break it.
- Chain order matters: security filters running in the wrong order cause real bugs.

**How I'd monitor it**
Patterns aren't monitored directly, but their effects are. For Strategy, log the chosen parser and court code and search by that field in Splunk to see which parser fails. Tag parse-time and error metrics by court. Watch transaction rollbacks and slow listener times. Use SonarQube complexity scores to spot the next `if/else` that should become a Strategy.

**Follow-ups to expect**
- *Is a Spring singleton the same as the GoF Singleton?* -> No. Spring creates one instance per container; the class itself isn't locked down, and the same class could be instantiated elsewhere.
- *Strategy vs Factory?* -> Strategy chooses behaviour; a factory creates objects. They often work together: a factory or map picks the right strategy.
- *How does `@Transactional` work?* -> Spring wraps the bean in a proxy that opens the transaction, calls your method, then commits or rolls back.

**60-second answer**
"I group patterns by the problem they solve. Strategy handles varying behaviour: in one project I had a parser per court behind one interface, so adding a court meant one new class instead of editing a giant if/else. Factory and Builder create objects cleanly. Adapter wraps vendor APIs so changes stay in one place. Spring gives me several for free: singleton beans, Template Method in `JdbcTemplate`, Proxy in AOP such as `@Transactional`, Observer through application events, and Chain of Responsibility in servlet and security filters. I only use a pattern when it removes real pain, because patterns for their own sake add complexity. I also know the pitfalls, like self-invocation bypassing a proxy."

### Q25 [mid] Strategy vs State vs Template Method?
tags: strategy pattern, state pattern, template method, design patterns, composition vs inheritance, spring, basics

**Start here: the concepts**
- **Design pattern**: a named, reusable way to structure code for a problem that keeps coming back. The name lets a team say "use Strategy" instead of explaining the whole design.
- **Interface and polymorphism**: an interface is a contract (method signatures). Polymorphism means the caller uses the contract and the actual object decides what the method does. All three patterns rely on it.
- **Strategy**: you have several interchangeable ways to do one job (for example parse CSV or parse XML). Each way goes in its own class behind one interface. The caller, usually called the context, is given one and uses it. It exists to remove big `if/else` blocks and to let you add a new way without editing old code.
- **State**: an object behaves differently depending on its current condition (an order that is NEW, PAID, SHIPPED or CANCELLED). Each condition becomes a class that knows what is allowed in that condition and what comes next. The object changes its own behaviour as it moves through states.
- **Template Method**: a base class fixes the order of steps (open, validate, parse, save). Subclasses fill in only the steps that differ. It uses inheritance, so the skeleton stays in one place.
- **Composition vs inheritance**: composition means an object holds another object and delegates to it (Strategy, State). Inheritance means a subclass extends a base class (Template Method).

**The live scenario**
An order service handles about 200,000 orders a day. `Order.process()` has a 40-line `if (status == ...)` chain repeated in five methods. A developer adds a REFUNDED status and forgets one chain. About 0.5% of orders, roughly 1,000 a day, take a wrong path, such as a cancelled order still being shipped. The same team also imports partner files in CSV, XML and JSON. Each importer copies the same "open, validate, parse, save" flow, and a fix to validation has to be made three times. They refactor in three ways:
- State for the order lifecycle.
- Strategy for the per-format parsers.
- Template Method for the shared import flow.

**What the interviewer is really checking**
Whether you can tell patterns apart by intent, not by class diagram, since Strategy and State look almost identical. They also want to see that you know when each one is worth using.

**How I answer it**
1. **Start with the shared shape.** Strategy and State both delegate work to an interchangeable object behind an interface. Say so, then split them by intent. That shows you understand more than the definitions.
2. **Strategy: who chooses?** The caller or configuration picks the algorithm from outside, and it usually stays the same for the object's life. The importer picks `CsvParser` or `XmlParser` by file type. The strategies don't know about each other.
3. **State: who changes?** The object moves between states itself, as work happens. `PaidState.cancel()` allows a refund, while `ShippedState.cancel()` throws an error. The rules for what is legal live in one class per state, so a forgotten `if` can't happen.
4. **Template Method: where is the variation?** The order of steps is fixed and only some steps vary. Use it when the flow must be identical and only details differ. The base class controls the flow, so subclasses can't skip validation.
5. **Show the example.** A `Parser` interface with `CsvParser` and `XmlParser` is picked from a registry keyed by file type. That is Strategy. In Spring you can inject a `Map<String, Parser>` keyed by bean name.
6. **Give the decision rule.** Ask "who chooses, and does it change over time?" Caller chooses once means Strategy. The object transitions itself means State. Fixed steps with a few variable parts means Template Method.

```java
abstract class Importer { // Template Method
  final void run(File f){ validate(f); save(parse(f)); }
  abstract List<Row> parse(File f); // step that varies
}
```

**Trade-offs and what can go wrong**
- All three add classes. For two stable options, a plain `if` or an enum is simpler.
- Template Method locks you into inheritance. One base class per subclass, and changes to the base can break every subclass. If the steps start to vary a lot, switch to Strategy.
- State can be over-used. If an order only has a status field and no behaviour changes, an enum is enough.
- Strategy needs a safe fallback. An unknown file type in the registry should fail clearly, not return null.
- State transitions scattered across classes can be hard to follow, so document the allowed transitions in one table.

**How I'd monitor it**
- Log every state transition (`orderId, from, to`) and alert in Splunk on illegal-transition exceptions, which should be near zero.
- Count imports per strategy and per file type, and alert on "no parser for type X".
- Track import duration and failure rate per parser, so a bad `XmlParser` release stands out.

**Follow-ups to expect**
- *Strategy and State have the same UML. What differs?* -> Intent. Strategy is chosen from outside and is usually stable. State changes by itself as the object moves through its lifecycle.
- *Template Method or Strategy for the importer?* -> Template Method when the flow is fixed and only a few steps differ. Strategy when you want to swap whole behaviours at runtime or avoid inheritance.
- *How do you add a new file type?* -> Add one new `Parser` class and register it. No existing code changes, which is the open/closed principle.

**60-second answer**
All three hide variation behind a clear structure, but for different reasons. Strategy lets the caller choose one of several interchangeable algorithms, like picking a `CsvParser` or `XmlParser` by file type from a registry. State is for an object whose behaviour changes as it moves through its own lifecycle, like an order going from paid to shipped, and each state class decides what is allowed. Template Method puts the fixed skeleton of a process in a base class and lets subclasses fill in only the steps that differ. The key split is that Strategy and State use composition, while Template Method uses inheritance. I decide by asking who chooses the behaviour and whether it changes over time. I'd also say that for two simple cases, an enum or an `if` is fine.

### Q26 [mid] Implement a thread-safe Singleton and say why Spring beans make it mostly unnecessary.
tags: singleton, thread-safety, class-loading, spring-beans, dependency-injection, design-patterns, basics

**Start here: the concepts**
- **Singleton**: a class that allows only one instance in the whole application. It exists for things that should be shared and created once, such as configuration, a connection pool or a cache.
- **Thread-safe**: correct when many threads use it at once. The classic bug is two threads each seeing "no instance yet" and each creating one, which breaks the "only one" rule.
- **Lazy initialization**: creating the object on first use, not at startup. It saves startup cost, but it is where the race happens.
- **Class loading guarantee**: the JVM initializes a class exactly once, and it holds an internal lock while doing so. Even if many threads touch the class at the same moment, its static initializer runs once. Both safe approaches below rely on this.
- **Enum singleton**: an `enum` with one constant, `enum Singleton { INSTANCE }`. The JVM creates the constant once. Enums also resist reflection and serialization attacks that can create a second instance of a normal class.
- **Holder idiom**: a private static inner class holds the instance. The inner class is not loaded until `get()` is first called, so you get laziness plus the JVM's one-time guarantee, with no `synchronized` code.
- **Spring bean / singleton scope**: Spring creates an object, called a bean, and hands the same instance to every class that asks for it. Singleton scope is the default. This is dependency injection (DI): a class receives its collaborators instead of fetching them through static calls.

**The live scenario**
A pricing service handled about 2,000 requests per second. A hand-written `getInstance()` had `if (instance == null) instance = new RuleLoader();` with no locking. After a deploy, several threads hit it in the first second. Three instances were created, and each loaded a roughly 50 MB rule set from the database. Heap spiked and startup slowed. Worse, the instances held slightly different rule versions, so a few customers got inconsistent prices. It was rare, hard to reproduce and only appeared under load.

**What the interviewer is really checking**
Whether you know why the naive version breaks, and whether you know safe alternatives. A mid-level candidate should also see that in Spring you rarely write this pattern by hand, and that "one instance" does not mean "thread-safe".

**How I answer it**
1. **Explain the failure first.** Two threads can both pass the null check before either assigns, so two instances get created. Fixing this is the whole point of a thread-safe singleton.
2. **Prefer the enum**, `enum Singleton { INSTANCE }`. It is one line and the JVM guarantees one instance. It also stays a singleton under serialization and reflection. The limit is that it cannot extend another class.
3. **Use the holder idiom when you need a normal class**:
```java
class Config { private Config(){}
  private static class H { static final Config I = new Config(); }
  static Config get(){ return H.I; } }
```
   `H` loads only on the first `get()`, and the JVM initializes it once under its own lock, so it is lazy and safe without explicit locking.
4. **If you use double-checked locking**, the field must be `volatile`. Without it, another thread can see a half-built object.
5. **In Spring, use a singleton-scoped bean** and inject it. This is testable because you can swap in a mock, whereas static access is hard to replace. It also gives you lifecycle management, with creation, configuration and shutdown handled by the container, and no hidden global state.
6. **Know the scope of "singleton".** A Spring singleton means one instance per application context, not one per JVM. The same class can exist twice if you run two contexts.

**Trade-offs and what can go wrong**
- Spring does not make a bean thread-safe. If a singleton bean holds mutable fields, such as a shared `SimpleDateFormat` or a request-specific value, concurrent requests will corrupt them. Keep beans stateless or immutable, or use thread-safe structures.
- Static singletons are global state. They make unit tests depend on each other and hide dependencies.
- The enum cannot extend a class, and the holder idiom can still be broken by reflection or serialization unless you guard against it.
- Lazy creation can move a slow initialization into the first user request. Eager creation costs startup time.

**How I'd monitor it**
- Log once in the constructor. In Splunk, search for that message and alert if it appears more than once per JVM.
- Check heap and startup time after deploys. Duplicate heavy instances show up as memory spikes.
- Write a concurrency test that calls `get()` from many threads and asserts all references are identical.
- In Spring, check `/actuator/beans`, if Actuator is enabled, to confirm scope. Take thread dumps if you suspect contention or races on shared bean state.

**Follow-ups to expect**
- *Why must the field be `volatile` in double-checked locking?* -> Without it, the compiler or CPU may reorder writes, so another thread can see a non-null reference to an object that is not fully constructed. `volatile` forbids that reordering.
- *Is a Spring singleton bean thread-safe?* -> No. Spring guarantees one instance per context, but any mutable state in it must still be made thread-safe.
- *When would you not use a singleton bean?* -> When the object holds per-request or per-user state. Use prototype or request scope, or pass the data as method arguments.

**60-second answer**
The naive singleton breaks because two threads can both see "no instance" and each create one. The safest simple fix is an enum with one constant, because the JVM creates it once and it survives serialization and reflection. If I need a normal class, I use the holder idiom. A private static inner class holds the instance, and the JVM initializes it once, lazily, on first use. If I write double-checked locking, the field has to be volatile. In Spring I would not hand-write any of this. I would make a singleton-scoped bean and inject it, which is easier to test and has no static access. I would also remember that Spring gives one instance per context but does not make it thread-safe, so beans must stay stateless or protect their mutable state.

### Q27 [mid] Builder vs telescoping constructors vs records?
tags: builder, records, telescoping-constructor, static-factory, immutability, java-16, basics

**Start here: the concepts**
- **Constructor**: code that runs when you create an object and sets its starting field values.
- **Telescoping constructors**: several constructors with a growing number of parameters, each calling the next, e.g. `Order(id)`, `Order(id, customer)`, `Order(id, customer, coupon, note)`. They exist because Java has no default or named arguments. They become unreadable, because `new Order("A1", null, null, "gift", true)` does not say what each value means.
- **Immutable object**: one whose fields cannot change after creation. It is safe to share between threads and easier to reason about.
- **Builder pattern**: a helper object where you set fields by name (`.customer("X").coupon("Y")`) and then call `build()` to get the finished object. It exists to make creation readable when there are many optional fields.
- **Record** (final in Java 16): a short way to declare an immutable data class. `record Money(long amount, String currency) {}` generates the constructor, getters, `equals`, `hashCode` and `toString`. Its fields are final, but only shallowly: a `List` inside can still be modified unless you copy it.
- **Compact constructor**: a record feature where you write validation code without repeating the parameter list.
- **Static factory method**: a named static method that returns an instance, e.g. `Money.of(5, "EUR")` or `Order.empty()`. The name explains intent.
- **Invariant**: a rule that must always hold, e.g. "amount is never negative".
- **Lombok `@Builder`**: an annotation that generates the builder code at compile time.

**The live scenario**
A refund service had a `RefundRequest` constructor with 9 parameters, and three of them were `String` (orderId, merchantId, reason). A developer swapped two. It compiled, passed a weak test and went live. About 300 refunds an hour (illustrative) went to the wrong lookup and failed. Switching to a builder with named setters removed this class of bug. The rule "amount must be positive" now lived in one constructor, so nothing could skip it.

**What the interviewer is really checking**
Whether you pick the construction style by the shape of the data (required vs optional fields, number of fields) rather than by habit. They also want to hear that you protect invariants and know the limits of records and Lombok.

**How I answer it**
1. **Few required fields, simple immutable data: use a record.** There is no boilerplate, and the compact constructor can validate. Example: `record Money(long amount, String currency)`.
2. **Many fields, especially optional ones: use a Builder.** Named setters make call sites readable and stop positional mix-ups. A common rule of thumb is to consider a builder at about 4-5 parameters or more, but it is a guideline, not a law.
3. **Avoid telescoping constructors.** Each new optional field forces another overload, and callers cannot tell the arguments apart.
4. **Use static factory methods when the name adds meaning**, such as `Money.zero()` or `Order.fromCart(cart)`. They can also return a cached instance or a subtype.
5. **Keep invariants in the constructor, and have `build()` call it.** Validating only inside the builder lets someone create an invalid object through another path. The constructor is the one place every path goes through.
6. **Use Lombok `@Builder` sparingly.** It saves typing but hides the generated code, and it does not validate anything. Put it on a constructor that validates, and check your Lombok version's support if you combine it with records.

```java
record Money(long amount, String currency) {
    Money { if (amount < 0) throw new IllegalArgumentException("negative"); }
}
```

**Trade-offs and what can go wrong**
- A builder adds code and a short-lived extra object. Hand-written, it is a lot of boilerplate.
- A record with 12 components has the same swapped-argument problem as a long constructor. Records are not a cure for large objects.
- Records are only shallowly immutable. Use `List.copyOf` in the compact constructor.
- Records cannot extend classes, and their field set is part of their public shape, so adding a field changes the API.
- A builder that skips required fields until runtime fails late. Make required fields constructor or factory arguments, or check them in the constructor.
- Overusing `@Builder` on every class is noise.

**How I'd monitor it**
- Unit tests that try invalid values and expect `IllegalArgumentException`.
- Code review and static analysis (Sonar or Checkstyle parameter-count rules) to flag constructors with too many parameters.
- In Splunk, search for the validation exception messages so that bad input from callers shows up as a count per service, e.g. `index=app "IllegalArgumentException" | stats count by service`.

**Follow-ups to expect**
- *Can you combine records and builders?* -> Yes. The builder collects values and calls the record's canonical constructor, so validation still runs. Many teams do this for records with many fields.
- *Is a builder thread-safe?* -> Usually not. Treat it as a single-thread, short-lived helper. The object it builds is the thing that is immutable and shareable.
- *Builder vs setters (JavaBean style)?* -> Setters leave the object half-built and mutable between calls. A builder gives you a complete, validated object in one step.

**60-second answer**
"I choose by the shape of the data. For simple immutable data with a few required fields I use a record, and I put validation in its compact constructor. For objects with many optional fields I use a builder, because named setters are readable and avoid mixing up arguments. I avoid telescoping constructors because they stack overloads and nobody can tell what each argument means. I use static factory methods when a name helps, like `Money.zero()`. Whatever style I use, the invariants live in the constructor, so `build()` just calls it and no path can create an invalid object. I use Lombok's `@Builder` only where it saves real boilerplate."

### Q28 [mid] What is Dependency Inversion vs Dependency Injection vs IoC?
tags: dependency-inversion, dependency-injection, inversion-of-control, solid, spring, design-principles, basics

**Start here: the concepts**
- **Dependency:** another class that your class needs to do its job. An `OrderService` that needs to charge cards depends on some payment code.
- **High-level vs low-level code:** high-level code holds business rules ("an order must be paid before shipping"). Low-level code holds technical details (calling Stripe over HTTP, writing to MySQL).
- **Abstraction:** an interface or abstract class that says *what* is done, not *how*. Example: `PaymentGateway.charge(...)`.
- **Dependency Inversion Principle (DIP):** the "D" in SOLID. High-level code should not depend on low-level code. Both should depend on an abstraction. The abstraction should be owned by the high-level side and shaped by its needs. The low-level class then has to conform to it, which is why the arrow is "inverted". It exists so that business rules survive when technical details change.
- **Dependency Injection (DI):** a technique where a class receives its dependencies from outside (usually through the constructor) instead of creating them with `new`.
- **Inversion of Control (IoC):** a broad idea where you hand control of something (creating objects, calling your code, managing lifecycle) to a framework instead of doing it yourself. "Don't call us, we'll call you."
- **IoC container:** Spring's `ApplicationContext`. It creates objects (beans), wires them together and manages their lifecycle. It is one implementation of IoC, and DI is how it delivers dependencies.

**The live scenario**
A team's `OrderService` created `new StripeClient()` inside itself. The business wanted a second payment provider for one region. Every change touched core order logic, and unit tests called the sandbox API at about 800 ms each. 400 tests meant over 5 minutes of build time, and flaky tests whenever the sandbox was slow. After the team introduced a `PaymentGateway` interface owned by the order module, wrote `StripeGateway` and `AdyenGateway` implementations, and let Spring inject one, tests used a fake and ran in seconds. Adding the second provider became a new class plus config.

**What the interviewer is really checking**
Whether you can tell a design principle (DIP) from a technique (DI) from a broader idea (IoC), and know they are related but not the same thing.

**How I answer it**
1. **Start with DIP, the "why".** Business rules should not import vendor or infrastructure classes. Reason: those details change often, and the business rules should not have to change with them.
2. **Say who owns the interface.** It lives with the high-level module. Reason: if the interface lived in the Stripe package, the dependency would still point at the low-level detail.
3. **Explain DI, the "how".** The class receives the abstraction from outside.
```java
class OrderService {
  private final PaymentGateway gateway;
  OrderService(PaymentGateway gateway) { this.gateway = gateway; }
}
```
Reason: the class no longer decides which implementation it gets, so you can swap one in or out.
4. **Explain IoC, the broadest idea.** Something else controls object creation and wiring. Spring's container reads your configuration, builds the beans and injects them. Reason: you stop writing wiring code and the framework manages lifecycle. DI is one way of doing IoC; others include template-method callbacks and event listeners.
5. **Tie them together.** DIP is the design goal, DI is the technique that achieves it, and an IoC container automates DI. DI alone does not give you DIP: injecting a concrete `StripeClient` is still DI, but the high-level class still depends on a detail.

**Trade-offs and what can go wrong**
- Over-abstraction: an interface for every class with one implementation adds noise. Abstract at real change points such as vendors, databases and external systems.
- Wiring errors surface at startup (missing or ambiguous beans) rather than at compile time.
- Circular dependencies. Spring Boot has rejected them by default since 2.6, which is good; fix the design rather than re-enabling them.
- Field injection hides dependencies and makes tests harder. Prefer constructor injection.
- Putting the interface in the low-level module breaks DIP even if you use Spring.

**How I'd monitor it**
- Build and unit-test time (a drop shows fakes replacing real calls) and flaky-test rate in CI.
- ArchUnit tests that fail the build if the domain package imports vendor packages.
- Splunk search on startup logs for `UnsatisfiedDependencyException` or `NoUniqueBeanDefinitionException` after deploys.
- Dependency-cycle reports from static analysis tools.

**Follow-ups to expect**
- *Can you use DI without DIP?* -> Yes. Injecting a concrete class is DI, but the high-level code still depends on a detail.
- *Why constructor injection over field injection?* -> Dependencies are explicit and final, the object is never half-built, and tests can create it without Spring.
- *Is Spring the only IoC?* -> No. IoC is a general idea. Spring, Guice and Jakarta CDI are containers, and plain manual DI (a `main` method that wires objects) works too.

**60-second answer**
Dependency Inversion is a design principle: business code should depend on an abstraction it owns, and low-level details like a payment vendor should implement that abstraction. Dependency Injection is a technique: a class gets its dependencies from outside, usually through its constructor, instead of calling `new`. Inversion of Control is the broader idea that a framework controls creation, wiring and lifecycle, and Spring's container is one example. So DIP is the goal, DI is how you achieve it, and the container automates it. DI alone is not DIP, because injecting a concrete class still couples you to a detail. In one of my projects, a `PaymentGateway` interface let us add a second provider and cut test time from minutes to seconds.

### Q29 [mid] Composition vs inheritance?
tags: composition, inheritance, oop, delegation, interfaces, fragile-base-class, design-principles, basics

**Start here: the concepts**
- **Inheritance**: a class `extends` another and automatically gets its fields and methods. It exists to reuse code and to say "this is a kind of that". Java allows only one parent class.
- **Is-a relationship**: "a `Car` is a `Vehicle`" is true in every situation. Inheritance should model only this kind of statement.
- **Composition**: a class holds another object in a field and uses it ("has-a"). A `Car` has an `Engine`. It exists so you can reuse behaviour without becoming that thing.
- **Base class (superclass)**: the parent being extended. The child is the subclass.
- **Fragile base class problem**: a subclass depends on how the parent works internally, not just on what it promises. A harmless-looking change in the parent can then break children you never touched.
- **Interface**: a contract listing methods, with no state. Many classes can implement it.
- **Delegation**: your class receives a call and passes it to the object it holds, which does the real work.
- **Tight coupling**: two pieces of code are so linked that changing one forces changes in the other.

**The live scenario**
A payments team had `BaseNotifier` with 12 subclasses (email, SMS, push, each in several variants). Someone changed `sendAll()` in the base class to call `send()` in a loop, to add logging. Two subclasses already overrode `sendAll()` and called `send()` themselves, so about 3% of customers (roughly 6,000 of 200,000 daily messages) got duplicates. Product then asked for "SMS with retry and rate limiting", and the team faced a combinatorial pile of subclasses like `RetryingRateLimitedSmsNotifier`. They refactored to a `Notifier` interface, where a `RetryingNotifier` wraps any other `Notifier`. New combinations then needed zero new subclasses.

**What the interviewer is really checking**
Whether you know the real reasons behind "prefer composition" (coupling, fragility, flexibility), and whether you can still say when inheritance is the right tool instead of repeating a slogan.

**How I answer it**
1. **Define the question by relationship.** Use inheritance only for a true, permanent is-a. Otherwise you inherit methods that make no sense for the child. The JDK has examples: `Stack extends Vector` exposes `insertElementAt`, which breaks stack behaviour.
2. **Check whether the base class is stable.** A subclass relies on the parent's internals, such as which method calls which. If the parent evolves, children break silently (the duplicate-message bug above). Inheritance is safe only when the base is stable or designed and documented for extension.
3. **Default to composition when unsure.** The class holds a collaborator and delegates to it. The reason is that the dependency is only on the collaborator's public contract, not its internals.
4. **Code to an interface, then delegate.** You get reuse without tight coupling:
```java
class RetryingNotifier implements Notifier {
  private final Notifier inner;           // any Notifier
  public void send(Msg m) { retry(() -> inner.send(m)); }
}
```
5. **Use composition for runtime flexibility.** You can swap the held object while the program runs (a different pricing rule per customer, say). A subclass is fixed at compile time.

**Trade-offs and what can go wrong**
- Composition needs more small classes and forwarding methods, which adds boilerplate.
- If the interface is large, delegation means writing many pass-through methods (IDEs and Lombok's `@Delegate` help).
- Inheritance is still the simpler choice for a stable hierarchy with a true is-a, such as extending an abstract class built for it.
- Common mistake: inheriting only to reuse a few methods, which creates a false is-a.
- Also avoid deep hierarchies (more than 2-3 levels). They are hard to read and hard to change.

**How I'd monitor it**
This is a design choice, so the checks are code-quality ones:
- Review depth of inheritance and "subclass overrides a concrete method" counts in static analysis (SonarQube or similar).
- Use ArchUnit-style rules to forbid extending certain concrete classes.
- Watch for failing subclass tests after a base class change.
- In code review, ask "is this really is-a?" for every new `extends`.

**Follow-ups to expect**
- *What is the Decorator pattern's link to this?* -> Decorator is composition in action. A wrapper implements the same interface and adds behaviour around the wrapped object (like `RetryingNotifier`).
- *When is inheritance the right choice?* -> When it is a true is-a, the base class is stable, and it was designed for extension, such as a template-method abstract class in your own framework.
- *Why can't you just make the base class `final`?* -> You can. That blocks the fragile base problem, but it also blocks all inheritance. Designing for extension and documenting it, or sealing it, is the middle path (Java 17 `sealed` classes control who may extend).

**60-second answer**
Inheritance means "is-a" and composition means "has-a". I prefer composition because inheritance couples a subclass to the parent's internals, so a small base class change can break children. That is the fragile base class problem. With composition I hold an object behind an interface and delegate to it, so I depend only on its contract and can swap it at runtime. I use inheritance when it is a genuine, permanent is-a and the base class is stable or designed for extension. For example, I once replaced a 12-subclass notifier hierarchy with a `Notifier` interface and wrapper classes for retry and rate limiting. That ended duplicate-message bugs and removed the need for a subclass per combination.

### Q30 [mid] What is Domain-Driven Design - the key terms?
tags: domain-driven-design, ddd, bounded-context, aggregate, microservices, value-object, basics

**Start here: the concepts**
- **Domain-Driven Design (DDD):** a way of building software where the code is shaped around the business problem, using the business's own words and rules. It exists because most project failures come from developers and business people misunderstanding each other, not from technology.
- **Ubiquitous language:** one shared vocabulary used by developers, product owners and the code itself. If the business says "Shipment", the class is `Shipment`, not `DeliveryRecord`. This removes translation errors.
- **Bounded context:** a boundary inside which a word has exactly one meaning. "Customer" means a billing account in Billing but a delivery address in Shipping. Each context has its own model.
- **Entity:** an object defined by its identity, not its attributes. Order #4711 stays the same order even if its status and items change.
- **Value object:** an object defined only by its values, immutable, and compared by value. Two `Money(10, EUR)` objects are interchangeable. Changing it means creating a new one.
- **Aggregate:** a cluster of entities and value objects treated as one unit for consistency. It has one **aggregate root**, the only entry point from outside. For example, `Order` is the root and its `OrderLines` are changed only through it. The root enforces rules such as "total cannot exceed the credit limit". The usual rule is one transaction changes one aggregate.
- **Repository:** an interface that loads and saves aggregates, so domain code does not know about SQL or Couchbase.
- **Domain service:** business logic that does not naturally belong to one entity, such as transferring money between two accounts.
- **Domain event:** a record that something meaningful happened, in past tense, such as `OrderPlaced`. Other parts of the system react to it.

**The live scenario**
A retail platform had one `Customer` table with 80 columns, shared by Billing, Shipping and Marketing, and three teams edited it. A change for a marketing flag broke invoice generation, and the same release caused about 40 failed invoices an hour for two hours. In a DDD workshop the teams found that each had a different meaning of "Customer". They split it into three bounded contexts. Each has its own model and talks to the others through events such as `CustomerAddressChanged`. Release conflicts dropped sharply, and each team deployed independently.

**What the interviewer is really checking**
Whether you know DDD is about modelling and boundaries, not just a list of terms, and whether you can link it to real design choices like microservice boundaries and transaction scope.

**How I answer it**
1. **Start with the problem DDD solves.** The business and the code drift apart. DDD fixes this with a shared language and clear boundaries.
2. **Split strategic from tactical.** Strategic DDD covers ubiquitous language and bounded contexts, which decide where the system divides. Tactical DDD covers entities, value objects, aggregates, repositories, domain services and events, which decide how the code inside one context looks.
3. **Explain entity versus value object with an example.** An Order is an entity, tracked by ID. `Money` is a value object, immutable and compared by value. This shows you understand identity versus equality.
4. **Explain the aggregate as a consistency boundary.** Rules that must always be true together live inside one aggregate, and the root protects them. Change one aggregate per transaction. Keep aggregates small, because large ones cause lock contention.
5. **Connect aggregates through events.** If placing an order must reserve stock, the `Order` aggregate saves and publishes `OrderPlaced`, and the Inventory context reacts. This is eventual consistency, so each transaction stays small.
6. **Link to architecture.** A bounded context is a good starting candidate for a microservice boundary. Business rules sit in domain objects and domain services, so controllers only translate HTTP to calls, which keeps them thin.

```java
interface OrderRepository { Optional<Order> findById(OrderId id); void save(Order order); }
```

**Trade-offs and what can go wrong**
- DDD is overkill for simple CRUD apps. The vocabulary and layering add cost with little gain.
- Huge aggregates, such as a `Customer` holding all orders, cause locking and slow loads.
- An "anemic model" is a common mistake. Entities hold only getters and setters while all the logic sits in service classes, so you pay the DDD cost and get none of the benefit.
- Bounded contexts are not always one service each. Splitting too finely creates distributed-system pain.
- Skipping the business conversations means you only rename classes and gain nothing.

**How I'd monitor it**
- Optimistic-lock or version-conflict exceptions per aggregate type. A rising count means the aggregate is too big or too contended.
- Splunk search on aggregate-save latency and on exceptions such as `OptimisticLockException`.
- For domain events: Kafka consumer lag and outbox backlog age, which show whether other contexts keep up.
- Coupling checks: the number of synchronous calls between contexts, and the number of teams that change a given module each release.

**Follow-ups to expect**
- *Why one aggregate per transaction?* -> It keeps locks short and the boundary clear. Cross-aggregate consistency is achieved with domain events and eventual consistency.
- *Is a bounded context the same as a microservice?* -> No. It is a model boundary, and a good candidate for a service boundary, but one service can host several contexts, especially early on.
- *Entity versus value object in practice?* -> If you care which one it is, it is an entity. If you only care what it holds, it is a value object, such as an address or an amount.

**60-second answer**
DDD means designing software around the business domain, using the business's own language in the code. That is the ubiquitous language. Systems are divided into bounded contexts, where each term has one meaning, and these often guide microservice boundaries. Inside a context, entities have identity, and value objects are immutable and compared by value. An aggregate is a group of objects with one root that enforces rules, and I change one aggregate per transaction. Repositories load and save aggregates, domain services hold logic that fits no single entity, and domain events tell other contexts what happened. The result is business logic in the domain, not in controllers.

### Q31 [mid] Explain Hexagonal (Ports & Adapters) / Clean Architecture.
tags: hexagonal architecture, clean architecture, ports and adapters, dependency rule, ArchUnit, testability, spring boot, basics

**Start here: the concepts**
- **Domain core:** the business rules (an order cannot ship unpaid, discounts, limits), written as plain Java classes. It exists so the rules that make the company money are not tangled up with technology choices.
- **Dependency rule:** source-code dependencies point inward only. Infrastructure code knows about the core, and the core never imports Spring, JPA, Kafka or HTTP classes. Because of this, changing a database or framework cannot break business logic.
- **Port:** an interface owned by the core that describes something it needs or offers.
  - *Outbound (driven) port:* what the core needs from the outside, e.g. `OrderRepository`, `PaymentGateway`.
  - *Inbound (driving) port:* what the core offers, e.g. a `PlaceOrderUseCase` interface.
- **Adapter:** a class that connects a port to a real technology.
  - *Outbound adapters* implement ports: a JPA repository, a REST client for the payment vendor.
  - *Inbound adapters* receive outside input and call a use case: REST controllers, Kafka consumers.
- **Use case (application service):** one business action, such as "place order". It coordinates domain objects and calls outbound ports.
- **Hexagonal vs Clean Architecture:** the same core idea, with different names and drawings. Hexagonal stresses ports and adapters. Clean Architecture draws concentric rings (entities, use cases, adapters, frameworks) with the same inward dependency rule.
- **ArchUnit:** a test library that checks package dependency rules, so the architecture is enforced by the build.

**The live scenario**
An order service handles about 300 orders per minute. Business logic sits inside `@Service` classes that use JPA entities directly and call the payment vendor's SDK. The vendor is replaced. The change touches 40 classes and takes three weeks, because vendor types leaked everywhere. Tests need `@SpringBootTest` with a database, so the suite takes about 12 minutes and developers stop running it. In the rewrite, the core defines `PaymentGateway`, and only one adapter knows the new vendor. The swap takes days, and core tests run in seconds with no Spring context. (Numbers are illustrative.)

**What the interviewer is really checking**
Whether you understand the dependency direction and why it matters (testability, replaceable infrastructure), not just the vocabulary. At mid level, they also want to hear that you have felt the cost of over-engineering.

**How I answer it**
1. **Put the business rules in a core with no framework imports.** Reason: the rules change for business reasons, and infrastructure changes for technical reasons. Keeping them apart stops one from forcing changes in the other.
2. **Let the core define the ports it needs.** The core owns the interface and speaks in domain terms, for example:
   ```java
   interface PaymentGateway { PaymentResult charge(OrderId id, Money amount); }
   ```
   Reason: if the vendor owned the interface, the core would depend on the vendor.
3. **Write adapters outside the core that implement those ports.** A JPA adapter maps database rows to domain objects, and a REST adapter calls the vendor. Vendor and database quirks stay inside these adapters.
4. **Make inbound adapters thin.** A controller or Kafka consumer converts the request into a use case call and converts the result back. Reason: transport details (HTTP, Kafka) stay out of the rules, so the same use case can later be triggered from a different entry point.
5. **Wire it together at startup.** Spring injects the adapters into the use cases. Reason: the core only sees interfaces, and the framework is used only as a wiring tool.
6. **Test in layers.** Test the core with fake ports (in-memory implementations). Test each adapter separately against a real or containerised dependency. Reason: this is fast and pinpoints failures.
7. **Enforce the dependency rule with ArchUnit in CI,** for example "domain packages must not depend on `org.springframework..` or `jakarta.persistence..`". Reason: architecture drifts silently without an automated check.

**Trade-offs and what can go wrong**
- More classes and mapping code (domain object to entity to DTO). For a simple CRUD service this is overkill.
- Ports shaped like the vendor's API (a "leaky port") remove the benefit.
- Keeping JPA annotations on domain classes is a common pragmatic shortcut. It is acceptable if you do it knowingly, but it breaks the pure rule.
- A "port for everything" habit creates pointless interfaces. Add a port where a real boundary exists.
- Anemic cores, where all logic ends up in adapters, defeat the purpose.

**How I'd monitor it**
- ArchUnit rules failing the build on any forbidden dependency.
- Core unit-test run time and share of tests needing a Spring context (both should stay low).
- Per-adapter metrics in Micrometer: latency and error rate for the payment adapter, the DB adapter and the consumer.
- Structured logs with the adapter name and a correlation ID, so a Splunk search such as `adapter=payment status=error` isolates vendor failures.

**Follow-ups to expect**
- *Difference between hexagonal and layered architecture?* -> In classic layers, the business layer often depends on the persistence layer below it. In hexagonal, the core owns the interfaces and infrastructure depends on it (dependency inversion).
- *Where do transactions go?* -> Usually at the use-case boundary (for example `@Transactional` on the application service). Keeping the domain model itself free of transaction annotations is a design choice.
- *Is it worth it for a small service?* -> Often not fully. Start simple, and introduce ports where you expect change or need isolation, such as external vendors.

**60-second answer**
Hexagonal, or Clean, Architecture keeps business rules in a core that does not depend on Spring, JPA or Kafka. The core defines ports, which are interfaces for what it needs, such as `OrderRepository` or `PaymentGateway`, and what it offers, the use cases. Adapters implement those ports with real technology: JPA, a REST client or Kafka on the outbound side, and controllers or consumers on the inbound side. The key rule is that dependencies point inward, so infrastructure knows the core and never the reverse. That gives fast core tests with fakes, and swapping a vendor or database means changing one adapter. I enforce the rule with ArchUnit in CI. The cost is extra classes and mapping, so I use it where boundaries really matter, not for trivial CRUD.

### Q32 [mid] What is an anti-corruption layer?
tags: anti-corruption-layer, ddd, adapter-pattern, integration, legacy-systems, microservices, basics

**Start here: the concepts**
- **Domain model:** the classes and vocabulary that describe your business in your own code, such as `CaseRecord` or `Hearing`. It should express your rules, not someone else's.
- **External or legacy model:** the data shapes and terms of a system you don't control, such as a vendor API or an old mainframe. Its names, codes and quirks follow its history, not your needs.
- **Leaking:** when the external model's concepts spread into your code, for example vendor status code `"07"` checked in twenty classes. Your code then depends on their design.
- **Anti-corruption layer (ACL):** a boundary layer that translates between the external model and your domain model, so only the ACL knows the external model exists. The term comes from Domain-Driven Design (Eric Evans). "Corruption" means your clean model being bent to fit theirs.
- **Adapter:** a design pattern that wraps one interface so it looks like another. It is the most common building block inside an ACL. The ACL itself is the wider idea: adapters, translators and sometimes a facade that hides a messy API.
- **Canonical record:** your own agreed internal shape of the data, which the rest of your system uses.

**The live scenario**
A court-records platform ingests case files from a vendor as XML, about 200,000 documents a day. At first, developers parsed the XML wherever they needed a field. The vendor then renamed `<CaseStat>` values and changed the date format. The fix touched 40 classes across 6 services and caused a 3-hour incident. The team then added one `VendorCourtRecordAdapter` that converts the XML into a canonical `CourtRecord`. After that, the next vendor change was a one-file fix with no downstream changes.

**What the interviewer is really checking**
Do you understand that this protects your domain model from outside change, and not just "convert XML to objects"? Can you say where the boundary sits and what it costs?

**How I answer it**
1. **Define my own canonical model first.** It is named in business terms and does not copy the vendor's field names. The reason is that the model should reflect how we think, not how the vendor stores things.
2. **Put all translation in one place.** The adapter parses the vendor payload and maps fields, codes and date formats into the canonical record. The reason is that when the vendor changes, exactly one module changes.
3. **Make the boundary one-directional in its dependencies.** The ACL depends on the vendor model, and the domain depends only on the canonical model. The vendor's types never appear in the domain's imports or method signatures.
4. **Handle bad or unknown data inside the ACL.** Map unknown codes to an explicit `UNKNOWN` value, reject or quarantine malformed records, and log them. The reason is that vendor mess should stop at the border and not reach the domain.
5. **Define the translation behind an interface.** A signature such as `CourtRecord toCanonical(VendorXml in)` lets me swap vendors or stub the vendor in tests.

**Trade-offs and what can go wrong**
- **Extra code and an extra hop:** there is mapping code to write, test and maintain, which is not worth it for a tiny, stable integration.
- **Lossy mapping:** if the canonical model drops vendor fields you later need, you must extend it deliberately.
- **Leaky ACL:** letting vendor DTOs (data transfer objects) slip past the boundary defeats the purpose.
- **A "god" translator:** one huge class mapping everything becomes the new legacy, so split it per aggregate or per vendor.
- **Not just an adapter:** if the vendor's behaviour differs (for example, different rules about when a case is closed), the ACL must translate semantics, not only field names.

**How I'd monitor it**
- **Mapping failures:** count them per vendor and per reason, and alert on a rising rate.
- **Unknown values:** count unmapped codes, which is an early warning that the vendor changed something. In Splunk, search for `unmapped_code` or `mapping_error` grouped by field.
- **Quarantine and dead-letter queue depth:** this shows rejected records waiting for review.
- **Vendor call latency and error rate:** this tells you whether a problem is theirs or yours.
- **Contract tests:** run sample vendor payloads through the adapter in CI to catch changes early.

**Follow-ups to expect**
- *How is an ACL different from an Adapter?* -> An Adapter is a single pattern that converts an interface. An ACL is an architectural boundary that protects a domain model and usually contains adapters, translators and possibly a facade.
- *When would you skip it?* -> When the external model is stable, simple and close to your own, or the integration is throwaway. Otherwise the layer costs more than it saves.
- *Where does it live in microservices?* -> At the edge of the service that consumes the external system. It can also be a separate translation service if several services share the same legacy system.

**60-second answer**
An anti-corruption layer is a translation boundary between my domain and an external or legacy system, so their concepts don't leak into my code. I define my own canonical model, then build an adapter that converts the other system's format into it. For example, it can turn a vendor's court-record XML into my `CourtRecord`. All field mapping, code conversion and bad-data handling live in that one place, so when the vendor changes something, I fix one module and not forty classes. It costs extra code and needs discipline so vendor types never cross the boundary. I'd monitor mapping errors and unknown codes, for example in Splunk, to catch vendor changes early.

### Q33 [senior] Anemic domain model vs rich domain model?
tags: domain-driven-design, anemic-domain-model, rich-domain-model, aggregates, invariants, application-service, spring, basics

**Start here: the concepts**
- **Domain model:** the classes that represent the business, such as Order, Payment and Customer, along with the rules of the business.
- **Invariant:** a rule that must always be true. For example, "a shipped order cannot get new items" or "the total equals the sum of its lines". Invariants exist so the data never reaches a state the business considers impossible.
- **Anemic domain model:** entities hold only fields with getters and setters. All the rules live in service classes (`OrderService`). It is easy to start with, but any code can call `setStatus(...)` and skip the rules.
- **Rich domain model:** the entity owns its data and its rules. You call `order.addItem(...)`, and the order itself checks that its status allows it. Callers cannot put it in an invalid state.
- **Aggregate:** a small cluster of objects treated as one unit, with one entry point called the aggregate root. Order is the root and its OrderLines are inside it. Outsiders only talk to the root, and the root protects the invariants. A transaction usually covers one aggregate.
- **Application service:** a thin class that orchestrates a use case. It loads the aggregate, calls a method on it, saves it, and publishes events. It does not hold the business rules.

**The live scenario**
An e-commerce order system handles about 200 orders per minute. Eight services and batch jobs call `order.setStatus(...)` directly. Each has its own copy of the "can we still change this order?" check, and two copies are slightly different. One Monday, support finds 140 orders where items were added after shipping. These orders had already been invoiced, so finance has to reconcile them by hand. The team moves the rule into `Order.addItem()`, which throws if the status is not OPEN. They make setters private. The class of bug disappears, because there is now only one place where the rule exists.

**What the interviewer is really checking**
Whether you understand where business rules belong and why. They also want to see that you are pragmatic: you know the rich model is not always right, and that you can avoid both a "bag of getters" and an over-engineered object graph.

**How I answer it**
1. **Define both models with one example.** Anemic is data plus a service; rich is behaviour next to data. A concrete example makes the difference clear fast.
2. **Name the real problem with anemic.** Rules get scattered and duplicated across services, so they drift apart. Any caller can create an invalid state, because nothing stops it.
3. **Show the rich fix.** The entity exposes intention-revealing methods and hides its setters:
   ```java
   public void addItem(Product p, int qty) {
       if (status != Status.OPEN) throw new IllegalStateException("Order not open");
       lines.add(new OrderLine(p, qty));
   }
   ```
   The rule has one home, and the caller cannot bypass it.
4. **Put invariants in aggregates.** The aggregate root guards the rules that must hold within one transaction. Keep aggregates small so locking and loading stay cheap.
5. **Keep orchestration in application services.** Transactions, loading, saving, calling other systems and publishing events belong there. Entities should not call repositories or make network calls, because that makes them hard to test and slow.
6. **Be pragmatic.** For simple CRUD, such as reference data or admin screens, an anemic model is fine. I go rich where the rules are valuable and change often, such as orders, pricing and payments.

**Trade-offs and what can go wrong**
- Rich models take more design effort and need a team that understands them. Beginners often find them harder to read than a simple service.
- Frameworks push you towards anemic. JPA needs a no-argument constructor, and JSON mappers like setters. Hide these (protected constructors, separate DTOs) rather than exposing the entity.
- Over-doing it produces "god entities" with hundreds of methods, or entities that call repositories and make remote calls.
- Aggregates that are too large cause lock contention and slow loads.
- Rules that span aggregates (for example stock across many orders) do not fit in one entity. Handle them in a domain service or with events and eventual consistency.

**How I'd monitor it**
- Unit tests that exercise invariants directly, with no Spring and no database. Fast tests are a sign the model is rich.
- Splunk search for domain exceptions such as "Order not open". A spike shows a caller breaking the rules, and the rule is now blocking it instead of corrupting data.
- Scheduled SQL or Mongo checks for impossible states, such as items on shipped orders. The result should stay at zero.
- Code review and static checks: flag public setters on aggregates and entity imports of repository classes.

**Follow-ups to expect**
- *Is anemic always an anti-pattern?* -> No. Fowler criticised it where real rules exist. For simple CRUD, it is a reasonable and cheaper choice.
- *Where does validation like "email format" go?* -> Input shape checks go at the edge (controller or DTO). Business invariants go in the aggregate.
- *How do you handle a rule across two aggregates?* -> Use a domain service for the decision, or publish an event and accept eventual consistency. Do not merge them into one huge aggregate.

**60-second answer**
In an anemic model, entities are only data and the rules live in services. That is easy to start with, but the rules get copied across services and any code can put an object into an invalid state. In a rich model, the entity guards its own invariants, so `order.addItem()` checks the status and callers cannot bypass it. I group objects into small aggregates, where the root protects the rules that must hold in one transaction. The application service stays thin and only loads, calls, saves and publishes events. I stay pragmatic: simple CRUD can stay anemic, while core areas like orders and payments get a rich model. I check it with fast domain unit tests and queries that look for impossible states.

### Q34 [senior] How do you manage technical debt as a Lead?
tags: technical-debt, engineering-leadership, refactoring, code-quality, sonarqube, archunit, strangler-pattern, basics

**Start here: the concepts**
- **Technical debt:** shortcuts or outdated design that make future changes slower or riskier. Like financial debt, you get speed now and pay "interest" later, as slower features and more bugs.
- **Debt register:** a shared list (a Jira label or a wiki table) of known debt items. Each item records what it is, what it costs (incidents, hours lost), and a rough fix effort. It exists so debt stops being a vague complaint and becomes something you can prioritise.
- **Capacity allocation:** reserving a fixed share of each sprint (15-20% is a common starting point, not a law) for debt work. Without it, feature work always wins.
- **Cost of delay:** what we lose for each week an item stays unfixed. Dividing it by effort gives a simple priority order.
- **Boy-scout rule:** leave the code slightly better than you found it. Small cleanups happen inside normal feature work.
- **Guard rails:** automated checks that stop new debt from entering.
  - A **SonarQube quality gate** fails the build if new code has too many bugs, too little test coverage or too much duplication.
  - **ArchUnit** is a Java test library that checks architecture rules, for example "controllers must not call repositories directly".
  - **Dependency update bots** (Dependabot, Renovate) open pull requests for outdated libraries.
- **Big-bang rewrite:** replacing a whole system at once. It is risky because the old system keeps changing while you rebuild it. The safer alternative is the **strangler approach**: replace one piece at a time behind the same interface.

**The live scenario**
An order service handles about 2,000 requests per minute. One 3,000-line `PricingService` class has weak tests. A small discount change takes 2 weeks instead of 2 days, and it caused 3 production incidents in a quarter. Product wants new features, and a developer proposes a 4-month rewrite. As Lead, you must reduce the pain without stopping delivery.

**What the interviewer is really checking**
Whether you treat debt as a business-risk and prioritisation problem rather than a "clean code" preference. They also want to see that you can negotiate with product, keep delivery going, and prevent debt from coming back.

**How I answer it**
1. **Make it visible with a debt register.** For each item I record the impact (incidents, hours lost, blocked features) and the effort. Product only funds what it can see and understand.
2. **Tie each item to business risk.** I write "pricing changes take 10 days and caused 3 incidents", not "the code is ugly". Incidents and slow delivery are the language of the business.
3. **Reserve a fixed capacity, such as 15-20% per sprint.** A standing budget avoids renegotiating every sprint, and debt work never gets squeezed out by the next deadline. I adjust the figure if incidents rise.
4. **Prioritise by cost of delay.** I rank by weekly cost divided by effort. A cheap fix on a hot path comes before an expensive fix on code nobody touches.
5. **Apply the boy-scout rule inside feature work.** When a feature touches `PricingService`, the developer adds tests and extracts one rule. Debt shrinks where change happens, so effort goes where it pays.
6. **Automate guard rails.** The Sonar quality gate applies to new code only, so legacy code does not block every build. ArchUnit tests protect layering, and a bot keeps dependencies current, since small frequent upgrades are easier than one huge one.
7. **Avoid giant rewrites.** I strangle instead: wrap the pricing logic behind an interface and move one rule at a time. Each step is shippable and reversible.

**Trade-offs and what can go wrong**
- A fixed percentage can turn into a dumping ground for low-value refactoring. Every item still needs a stated benefit.
- Strict quality gates on legacy code cause the team to ignore or bypass them. Gate new code only.
- Some debt is deliberate and fine, such as a shortcut for a launch date, if it is recorded and has a payback date.
- Boy-scout cleanups without tests can introduce bugs. Add tests first.
- A strangler migration is slower than a rewrite on paper, but it delivers value early and carries far less risk.

**How I'd monitor it**
- Sonar new-code metrics: coverage, duplication, and the number of new issues.
- Incident count and change failure rate per component. Splunk searches grouping errors by service and exception class show repeat offenders.
- Lead time for changes in the hot modules, for example pricing (the DORA metrics).
- Age and count of open debt-register items, and the share of sprint capacity actually spent.
- Number of outdated dependencies and known vulnerabilities.

**Follow-ups to expect**
- *How do you convince product to give you capacity?* -> Show the data: incidents, delayed features and hours lost, with a small plan whose benefit can be measured within a few sprints.
- *When is a rewrite justified?* -> When the technology is unsupported or incompatible with requirements and the system is small enough to replace safely. Even then, migrate incrementally and run both in parallel.
- *How do you handle debt you create under deadline pressure?* -> Log it in the register with an owner and a date, and schedule it in the next sprints.

**60-second answer**
"I first make debt visible in a register, with the impact of each item in incidents and lost days, so product sees it as business risk. I reserve a steady share of every sprint, roughly 15-20%, and rank items by cost of delay against effort. Inside normal feature work we follow the boy-scout rule and add tests where we touch the code. To stop new debt, I add guard rails: a Sonar quality gate on new code, ArchUnit tests for architecture, and automated dependency updates. I avoid big rewrites and replace risky parts step by step behind an interface. I track incidents, lead time and quality-gate trends to show it is working."

### Q35 [senior] Code review: what do you look for and how do you give feedback?
tags: code-review, java, spring-boot, testing, security, team-practices, basics

**Start here: the concepts**
- **Code review:** another engineer reads your change before it merges. It exists to catch defects early, spread knowledge and keep the codebase consistent.
- **Edge case:** an unusual input or state, such as null, an empty list, a duplicate request, a timeout or a very large value. Most production bugs live here.
- **Injection:** attacker-supplied text gets run as code or a query, as in SQL built by string concatenation. The fix is parameterised queries.
- **Authz (authorisation):** checking that this user is allowed to do this action on this record. It differs from authentication, which only proves who the user is.
- **Secrets:** passwords, API keys and tokens. They must never be in source code or logs.
- **N+1 query:** one query loads N parents, then N more queries load each parent's children. Latency grows with N.
- **Blocking call:** a thread waits on slow I/O. If many threads wait, the thread pool runs out and the service stalls.
- **API compatibility:** existing callers keep working after your change. Removing or renaming a JSON field breaks them.
- **Observability:** logs, metrics and traces that let you see what the code does in production.
- **Nit:** a minor, optional style comment. A must-fix blocks the merge.
- **Linter/formatter:** tools that enforce style automatically, so humans don't argue about braces.

**The live scenario**
A pull request adds an "order history" endpoint. It looks fine, and a quick review would approve it. A careful reviewer notices three things:
- It loads 50 orders, then runs one query per order for its items. That is 51 queries per call, and at about 200 requests per second it would flood the database.
- It fetches orders by `orderId` from the URL without checking that the order belongs to the caller. Any user could read another user's orders.
- It has no test for an empty history.

The reviewer leaves these as must-fix comments, each with its reason. Two weeks later a similar endpoint without this review slows down under load. Catching the problem in review cost minutes, while the same fix in production cost an incident.

**What the interviewer is really checking**
Whether you review for risk (correctness, security, performance, compatibility) rather than style. Also whether you can give feedback that improves the code without damaging the relationship, and whether you automate the boring parts.

**How I answer it**
1. **Understand the intent first.** I read the description and the tests before the code. Without that I can't judge whether the code solves the right problem.
2. **Check correctness and edge cases.** I look for null, empty, duplicate, concurrent and failure inputs. A feature that passes only the happy path fails in production.
3. **Check tests.** They should cover the behaviour and the edge cases, and they should fail if the code is wrong. Tests are the safety net for later changes.
4. **Check security.** I look for injection, missing authorisation, and secrets in code or logs. These bugs are costly and easy to miss.
5. **Check performance.** I look for N+1 queries, blocking calls on request threads and unbounded loops or result sets. These work on a developer laptop and fail at load.
6. **Check error handling, logging and observability.** Errors should not be swallowed. Logs should carry context but no secrets or personal data. Important paths should have metrics so we can see them in production.
7. **Check API compatibility.** I look for renamed fields, changed status codes or changed event formats. Other teams' code depends on them.
8. **Check readability and naming.** Code is read far more often than it is written, and clear names reduce future bugs.
9. **Give feedback well.**
   - Be specific: point at the line and say what you suggest.
   - Explain why: "this runs one query per order, which gets slow with long histories".
   - Prefer questions to commands: "What happens if the list is empty?" invites thinking and may reveal context I missed.
   - Separate must-fix from nits, for example with a `nit:` prefix, so the author knows what blocks the merge.
   - Automate style with a formatter and linter in CI, so human attention goes to design and risk.

**Trade-offs and what can go wrong**
- Huge pull requests get shallow reviews, so I ask for small, focused changes.
- Nitpicking everything slows delivery and demoralises the author.
- A slow review queue is a cost too, so I aim to review within a working day.
- Tone matters: harsh comments make people defensive and hide problems.
- Reviewers can miss what is absent, such as a missing authorisation check or test. I use a checklist to catch these.
- Review is not a substitute for tests or CI.

**How I'd monitor it**
- Review turnaround time and pull request size.
- Defects that escape to production, traced back to what review missed.
- CI results for lint, tests and security scans.
- Post-incident reviews: "would a review check have caught this?" If yes, I add it to the checklist.

**Follow-ups to expect**
- *How do you handle disagreement with the author?* -> I explain my reasoning with evidence, such as a test, a benchmark or a link to a standard. If we still disagree, I bring in a third person or follow the team's convention. Critical risks stay blocking.
- *How do you review a very large PR?* -> I ask to split it. If I can't, I review by layers: design and API first, then logic, then tests.
- *How do you stop style debates?* -> I agree on a formatter and linter, enforce them in CI, and leave style out of human review.

**60-second answer**
I review for risk first. I check that the code is correct, including edge cases, that it has real tests, and that it is secure: no injection, proper authorisation and no secrets in code or logs. Then I check performance, such as N+1 queries and blocking calls, plus error handling, logging, observability and API compatibility, and finally readability and naming. When I give feedback, I am specific and explain why. I ask questions rather than give orders, and I mark what must be fixed versus what is only a nit. I automate style with a formatter and linter, so humans spend their time on design. I keep reviews fast and pull requests small, and I track escaped defects to improve the checklist.

### Q36 [senior] Event-driven architecture: events vs commands vs messages?
tags: event-driven, kafka, messaging, commands, events, schema-versioning, basics

**Start here: the concepts**
- **Message**: any piece of data one service sends to another through a channel such as a Kafka topic or a queue. It is the general word. Events and commands are both kinds of message. The "envelope" is the wrapper (headers, key, ID, timestamp) around the business content.
- **Event**: a record that something already happened, such as `OrderPlaced`. It cannot be refused, because it is history. The producer publishes it and does not know or care who reads it. Zero, one or many consumers may react.
- **Command**: a request to do something, such as `ChargeCard`. It is addressed to one specific handler, which can accept or reject it. The sender expects the work to be done.
- **Producer and consumer**: the producer sends messages and the consumer reads them.
- **Coupling**: how much one service must know about another to work. Low coupling lets teams change services independently.
- **Schema versioning**: giving the message's field layout a version so it can change without breaking existing readers.

**The live scenario**
An e-commerce platform handles about 200 orders per second at peak. Originally, Checkout called Email, Inventory and Analytics one by one. When Analytics slowed down, checkout latency rose from 150 ms to 2 s. The team changed Checkout to publish an `OrderPlaced` event to a Kafka topic, and the three services subscribe independently. Payment stayed a command, `ChargeCard`, sent to the Payment service only, because exactly one party must charge the card, once. A month later someone renamed the field `total` to `amount` in the event. Analytics crashed, and nobody had known it depended on that field.

**What the interviewer is really checking**
Whether you pick the message type by intent (a fact versus a request), and whether you understand that "decoupled" still needs a disciplined contract.

**How I answer it**
1. **Define by intent.** An event says "this happened"; a command says "please do this". Intent decides who owns the decision. With a command, the sender decides. With an event, each receiver decides its own reaction.
2. **Use events for fan-out.** Many services react to one fact, and the producer needs no code change to add another consumer. That removes the "call everyone in turn" problem from the scenario.
3. **Use commands for one owner.** When exactly one handler must act, a command makes that explicit, and the sender can expect a result or a failure.
4. **Treat "message" as the transport.** Both kinds travel as messages, and the envelope carries metadata. I include an event ID, a timestamp, a schema version and a correlation ID so I can trace and de-duplicate.
5. **Name events in the past tense** (`OrderPlaced`, not `PlaceOrder`). Commands use the imperative. The name stops events from quietly turning into disguised commands.
6. **Keep payloads stable and versioned.** Other teams depend on the payload. Only add optional fields. Never rename or remove fields without a new version. Consumers should ignore unknown fields.
7. **Avoid hidden coupling.** Publish a deliberate business contract, not your internal database entity. Consumers should not need to know how the producer works inside.

**Trade-offs and what can go wrong**
- Events are harder to follow end to end, because no single place shows the full flow. You need tracing.
- Event consumers may see duplicates or out-of-order messages, so handlers must be idempotent (safe to run twice).
- Disguised commands: publishing `SendEmailRequested` as an "event" when you really expect one specific service to act.
- Fat events leak internal data, and thin events force consumers to call back to the producer, which brings back coupling.
- Breaking a schema without warning, as in the `total` to `amount` rename.

**How I'd monitor it**
- Consumer lag per consumer group (Kafka metrics or Burrow-style tooling), with an alert if it keeps growing.
- Dead-letter topic counts and deserialization errors. A spike after a deploy suggests a schema break.
- A schema compatibility check in CI, for example a schema registry's backward-compatibility mode.
- Splunk searches on the correlation ID to follow one order across services. Alert on error rates grouped by event type and schema version.

**Follow-ups to expect**
- *How do you evolve an event without breaking consumers?* -> Add optional fields only, keep old ones, version the schema, and run a compatibility check in CI. For a breaking change, publish a new event version in parallel and retire the old one after consumers migrate.
- *Can a command go over Kafka?* -> Yes, but it needs one logical handler (a dedicated topic read by one consumer group) and a way to report the result or failure. A queue or a direct call is often simpler.
- *How do you publish an event reliably after a database write?* -> Use the outbox pattern. Write the event to an outbox table in the same transaction as the business data, then a separate process publishes it.

**60-second answer**
An event is a fact that already happened, like `OrderPlaced`. The producer doesn't care who listens, and many consumers can react. A command is a request, like `ChargeCard`, sent to one handler that can accept or reject it. A message is just the transport wrapper that carries either one. I name events in the past tense and keep their payloads stable and versioned. Consumers must not depend on the producer's internals, or the "decoupled" design is coupled in secret. In production I watch consumer lag and dead-letter counts, and I check schema compatibility in CI.

### Q37 [senior] Feature flags - benefits and risks?
tags: feature-flags, canary-release, kill-switch, progressive-delivery, flag-debt, release-management, basics

**Start here: the concepts**
- **Feature flag (toggle):** an `if` in the code whose answer comes from configuration, not from the build. Code for a new feature ships switched off, and someone turns it on later without redeploying. It exists so that shipping code and exposing it to users become two separate decisions.
- **Deploy vs release:** deploy means the new code runs on servers. Release means users can see the behaviour. Without flags these happen together, so every deploy is a risky business event.
- **Canary release:** expose the feature to a small slice of traffic (for example 1%) first, watch for problems, then widen it.
- **Kill switch:** a flag that turns a feature off instantly if it misbehaves. It is much faster than a rollback because no build or deploy is needed.
- **A/B test:** show version A to one group and version B to another, then compare a business metric. The flag does the splitting, but you still need measurement tooling to read the result.
- **Flag debt:** old flags that nobody removed. They leave dead branches and confusing code behind.
- **Combinatorial testing:** with N independent flags there are up to 2^N behaviours. You cannot test them all.
- **Hidden coupling:** two flags that secretly depend on each other, so turning on one without the other breaks something.
- **Flag platform:** a service (LaunchDarkly, Unleash) that stores flags, targets users or percentages, and keeps an audit log. Spring Cloud Config is a general configuration server, not a flag product. It can hold simple on/off values, but it lacks percentage rollouts and targeting, and values only update after a refresh (for example `@RefreshScope`). AWS AppConfig has a feature-flag mode with gradual rollout.

**The live scenario**
A checkout service handles about 2,000 requests per second. The team rewrites the payment-routing logic. Before flags, a bad release meant a 25-minute rollback, with roughly 5% of payments failing meanwhile. With a flag, the new code deploys on Tuesday but stays off. On Wednesday it goes to 1% of users, and the error rate rises from 0.2% to 3% in that slice. Someone switches the flag off in seconds, and only about 1% of traffic was ever affected. Months later, 40 stale flags remain and nobody knows which are safe to delete. That is the flag-debt side of the story.

**What the interviewer is really checking**
Whether you see flags as a release-control tool with a lifecycle, not just an `if` statement. A senior answer must cover discipline: ownership, expiry, testing and failure behaviour.

**How I answer it**
1. **Separate deploy from release.** Merge small changes to main behind a flag that defaults to off. Reason: code reaches production continuously, and risk is taken only when you turn the flag on.
2. **Roll out gradually.** Go 1% → 10% → 50% → 100%, checking metrics at each step. Reason: a bug hits few users, and you learn from real traffic that staging cannot reproduce.
3. **Keep a kill switch for risky paths.** Reason: turning a flag off takes seconds, while a rollback takes a full pipeline run.
4. **Use flags for experiments only with proper measurement.** Reason: a flag splits users, but without sticky assignment (the same user always sees the same variant) and a metric pipeline, the result is meaningless.
5. **Choose the platform by need.** Use LaunchDarkly or Unleash for targeting, audit and percentage rollout. Use AWS AppConfig or Spring Cloud Config for simple on/off values. Reason: config servers are cheaper, but you must build your own targeting and refresh logic.
6. **Give every flag an owner and an expiry date.** Create a cleanup ticket when you create the flag. Reason: a flag is temporary scaffolding, and unowned flags become permanent debt.
7. **Define a safe default.** If the platform is unreachable, the code uses a local cached value or a hard-coded default. Reason: the flag system must never become a single point of failure.

```java
if (flags.isEnabled("new-payment-routing", user)) newRouter.pay(o); else oldRouter.pay(o);
```

**Trade-offs and what can go wrong**
- Every flag doubles the paths to test. Test the on and off states, and keep the number of live flags small.
- Flags that depend on each other cause hard-to-reproduce bugs. Avoid chained flags.
- Removal is skipped. Once the rollout is at 100%, delete the flag and the old code path promptly.
- Anyone who can flip a flag can change production. Use permissions, audit logs and approvals for sensitive flags.
- Long-lived flags (permissions, operational switches) are legitimate, but label them as permanent so they are not mistaken for debt.
- Flipping a flag that changes data formats can leave data written by the new path unreadable by the old one. Plan the rollback with the data in mind.

**How I'd monitor it**
- Tag metrics and logs with the flag state, then compare error rate and latency (p95, p99) between flag-on and flag-off groups during the rollout.
- Run a Splunk search on the logged flag name and variant to see errors by variant.
- Alert when the error rate of the on-group exceeds the off-group by a set margin.
- Report flags past their expiry date or older than 90 days (illustrative threshold).
- Review the platform audit log to see who changed what and when.

**Follow-ups to expect**
- *How do you test with many flags?* -> Test each flag's on and off states in isolation, plus the few combinations that really interact. Keep flags short-lived so the matrix stays small.
- *What if the flag service goes down?* -> The SDK serves cached values and falls back to coded defaults, which should be the safe (usually off) behaviour.
- *Flag vs. config property?* -> Config tunes behaviour (timeouts, limits) and rarely changes. A flag switches a code path, is often per-user, and should be temporary.

**60-second answer**
Feature flags separate deploying code from releasing it. I ship code switched off, turn it on for 1% of users, watch the metrics, and widen gradually. If something breaks, a kill switch turns it off in seconds instead of a slow rollback. They also enable A/B tests, though that needs real measurement. The risks are flag debt, an explosion of combinations to test, and hidden coupling between flags. So every flag gets an owner and an expiry date, and I delete it once the rollout is complete. I would use a platform like LaunchDarkly or Unleash for targeting, or AWS AppConfig for simpler cases. I always define a safe default in case the flag service is unreachable.

### Q38 [architect] Design an extensible parser framework for 100+ file formats/sources.
tags: system-design, design-patterns, strategy-pattern, plugin-registry, streaming, data-ingestion, basics

**Start here: the concepts**
- **Parser**: code that reads raw bytes of one format (CSV, XML, fixed-width, EDI) and turns them into structured records.
- **Strategy pattern**: one interface with many interchangeable implementations. The caller picks one at runtime without knowing the details. Here, `FileParser` is the strategy and each format is one implementation.
- **Registry**: a lookup component that finds all parsers at startup and picks the right one for a file. It exists so that adding a format never means editing a big `if/else`.
- **Discovery**: how the registry finds parsers. Options are Spring beans (the container injects all `FileParser` beans), `ServiceLoader` (plain-Java plugin mechanism using files in `META-INF/services`), or Quarkus CDI (Quarkus's injection model).
- **Canonical record schema**: one agreed internal shape that every source is converted into. Downstream code then deals with one model, not 100.
- **Schema versioning**: a version number on that shape so it can evolve without breaking older data or consumers.
- **Mapping config**: per-source settings (column X maps to field Y, date format, delimiter). Many sources differ only in config, not code.
- **Streaming parsing**: reading and emitting one record at a time, so a 3 GB file never has to sit in memory.
- **Quarantine**: a side store for rows that fail validation, kept with the reason, so one bad row doesn't kill the file.
- **Contract test**: a test that feeds a real sample file of each source to its parser and checks the exact output.

**The live scenario**
A data platform ingests files from 120 partners: about 40,000 files a day, from 10 KB to 3 GB. The first version was one big `switch` on file extension. Onboarding a partner took two weeks and touched shared code. A 2 GB file loaded fully into the heap caused an OutOfMemoryError that stopped ingestion for everyone. One malformed row rejected a whole 500,000-row file. The rewrite moved to a plugin-style framework.

**What the interviewer is really checking**
Whether you can separate what changes (formats) from what stays stable (pipeline, schema, operations). They also want to see you cover memory, bad data and testing, not just "use Strategy".

**How I answer it**
1. **Define a small contract.** `supports(FileMeta)` and `parse(InputStream)` returning a lazy `Stream<Record>`. Reason: a tiny interface keeps each parser independent, and a lazy stream gives memory safety by design. Name the type something like `CanonicalRecord`, since `Record` clashes with Java's `java.lang.Record` (Java 16+).
   ```java
   interface FileParser { boolean supports(FileMeta m); Stream<CanonicalRecord> parse(InputStream in); }
   ```
2. **Build a registry that discovers parsers.** Use Spring beans, `ServiceLoader` or Quarkus CDI, depending on the stack. Reason: a new format becomes a new class or module with no edits to core code. Make selection deterministic: match on source ID first, then content type, and fail loudly if two parsers match.
3. **Convert everything to a versioned canonical schema.** Reason: downstream systems depend on one model, and versioning lets you evolve it safely.
4. **Put per-source differences in mapping config.** Reason: many CSV-like partners need no new code, only a config entry, which cuts onboarding time sharply.
5. **Stream, never load whole files.** Whoever consumes the stream must close it (try-with-resources), or file handles leak.
6. **Validate each row and quarantine failures.** Reason: partial success beats all-or-nothing, and quarantined rows can be fixed and replayed.
7. **Write contract tests with real sample files per source.** Reason: with 100+ parsers, a change to shared code must prove it broke none of them.
8. **Add metrics per parser and a Picocli CLI.** The CLI lets developers and support run a parser locally on a sample file, with no full environment.

**Trade-offs and what can go wrong**
- A canonical schema can become a lowest common denominator, or grow into a bloated superset. Allow a typed "extras" map and review changes.
- Too much config turns into a hidden programming language. Move complex logic into code.
- Plugins on the same classpath share dependencies, so version conflicts are possible. Isolate if needed.
- Streams are lazy, so errors surface mid-file. Decide the policy up front: skip the row, or fail past an error threshold.
- Sample files can contain personal data, so anonymise them.

**How I'd monitor it**
Per parser: files, rows per second, parse time, quarantine rate and failure count. Alert when the quarantine rate for a source jumps (usually a partner changed their format), when JVM heap grows with file size, or when "no parser found" appears. In Splunk, search by source ID and file ID to trace one file end to end.

**Follow-ups to expect**
- *How do you handle a format change from a partner?* -> Version the mapping or parser, route by file metadata, and let the contract test with the new sample prove compatibility. Quarantine-rate alerts catch it early.
- *What about files too big even to read in one pass, or needing parallelism?* -> Split by record boundaries where the format allows (e.g. line-based), process chunks in parallel, and checkpoint progress so a retry resumes.
- *How do you add a parser without redeploying?* -> Load plugin JARs with `ServiceLoader` from a directory, with the cost of dependency isolation and stricter governance.

**60-second answer**
I'd define a small `FileParser` interface with `supports` and a streaming `parse`, so each format is one interchangeable implementation. A registry discovers them through Spring beans, `ServiceLoader` or CDI and picks one deterministically. Every parser outputs a versioned canonical record, and per-source differences live in mapping config, so many onboardings need no code. We stream records so large files never fill memory, and we validate each row, sending bad ones to quarantine instead of failing the file. Each source has contract tests with real sample files, per-parser metrics, and a Picocli CLI for local runs. The main risks are a bloated canonical schema and config that turns into code, so I'd govern both.

### Q39 [architect] Design an audit-trail capability for an ERP.
tags: audit-trail, erp, system-design, hibernate-envers, cdc, outbox-pattern, multi-tenancy, basics

**Start here: the concepts**
- **Audit trail:** a permanent record of who changed what, when, and what the values were before and after. It exists so you can answer auditors, regulators and fraud investigators.
- **Entity listener / Hibernate Envers:** JPA entity listeners are callbacks that run when an entity is saved, updated or deleted. Envers is a Hibernate module that uses the same hooks to write a history row automatically for each change.
- **CDC (change data capture):** a tool such as Debezium reads the database's own transaction log and emits every row change as an event. It sees changes made by any application, script or DBA.
- **Append-only store:** a store where you only add records and never update or delete them, so history cannot be quietly rewritten.
- **Correlation id and tenant:** the correlation id is one id carried through every service call for a request, so you can join the audit row to logs. The tenant is the customer company in a multi-tenant ERP.
- **Outbox pattern:** you write the business change and an "event to publish" row in the same database transaction. A separate relay then ships the event onward, so you never have a change without its event, or the reverse.
- **Tamper evidence (hash chain):** each record stores a hash of its content plus the previous record's hash. Editing any old row breaks every hash after it.

**The live scenario**
An ERP serves 200 tenants. A finance auditor asks: "Who changed vendor bank account X from 4471 to 9902 last March, and from which request?" The team has only a `last_modified_by` column, so they cannot answer. Later, a DBA's direct SQL fix changes 3,000 invoices and no history exists. Assume 300 sensitive writes/sec at peak and about 1 KB per audit record. That is roughly 26 GB/day, or about 9 TB/year, so storage and retention have to be designed up front.

**What the interviewer is really checking**
Whether you treat audit as a reliability and trust problem rather than a logging feature. That means no lost records, no silent edits, bounded cost, and a design that covers every write path.

**How I answer it**
1. **Clarify requirements.** Which entities are sensitive (bank details, prices, permissions, approvals)? How long must data be kept? Must it be legally defensible? Auditing everything is expensive and noisy, so I audit sensitive entities only.
2. **Define the record.** Each record holds who (user and service identity), what (entity, id, action), when (server timestamp), before and after values, correlation id and tenant. Without the correlation id you cannot link a change to a request. Without the tenant you cannot isolate or query per customer.
3. **Choose the capture method.** Entity listeners or Envers are simple and run inside the application, so they know the user. Their gap is that bulk JPQL updates, native SQL and manual DBA fixes bypass them. CDC catches every change, but the log does not know the application user. So the app must write user and correlation id into the row, or into a transaction-context table, for CDC to pick up. For an ERP I would use Envers or listeners for rich business context, plus CDC as a safety net for out-of-band changes.
4. **Decide transactional behaviour.** For strict compliance, write the audit row in the same transaction as the business change, so both commit or neither does. For heavy volume or a separate audit service, write to an outbox table in that same transaction and relay it asynchronously (for example through Kafka). The audit store is then eventually consistent but never loses an event. Consumers must be idempotent, because the relay delivers at least once.
5. **Pick the store and protect it.** Use an append-only store with a restricted writer account that has INSERT only, with no UPDATE or DELETE grants. Add a hash chain per tenant, and periodically anchor the latest hash somewhere separate, such as a write-once (WORM) bucket.
   ```
   hash_n = SHA-256(record_n + hash_(n-1))
   ```
6. **Retention and search.** Partition by tenant and month. Keep recent data hot and searchable, and archive older data to cheap storage until the legal retention period ends. A search UI queries by entity, user, tenant, date range and correlation id, and is itself role-restricted and audited.

**Trade-offs and what can go wrong**
- Same-transaction writes add latency and make audit failures block business work. The outbox avoids that but adds lag.
- Envers doubles write volume and can bloat tables. Listeners miss bulk and native SQL changes.
- A hash chain serialises writes per chain, so use one chain per tenant or per partition.
- Do not store secrets or personal data in before/after values without masking, because the audit trail then becomes a privacy liability.
- Deleting data for privacy requests conflicts with immutability, so plan for redaction or crypto-shredding.

**How I'd monitor it**
- Outbox backlog age and relay lag, with an alert above a threshold.
- Consumer lag on the audit topic.
- Daily reconciliation: count of business changes vs audit records per tenant.
- A scheduled job that verifies hash chains and alerts on a break.
- Splunk searches for audit-write failures and for any non-audit account touching the audit store.
- Storage growth per day against the forecast.

**Follow-ups to expect**
- *Why not just log to files?* -> Logs are not queryable, are mutable, rotate away, and cannot guarantee that the change and its record both exist.
- *How do you capture the user in CDC?* -> Write user id and correlation id into the row or a context table within the same transaction, so the log carries them.
- *How do you prove nobody edited history?* -> Per-tenant hash chain plus periodic anchoring of the head hash in WORM storage.

**60-second answer**
I start by deciding which entities are sensitive and how long records must be kept. Each audit record holds who, what, when, before and after values, a correlation id and the tenant. I capture changes with Hibernate Envers or entity listeners because they know the user. I add CDC as a safety net for bulk SQL and DBA changes that bypass the application. For strict compliance I write the audit row in the same transaction. At higher volume I write to an outbox in that transaction and relay it asynchronously, so nothing is lost. The store is append-only, written by an insert-only account, with a hash chain so edits are detectable. I partition by tenant and date, archive per the retention policy, and put a restricted search UI on top. I monitor outbox lag, reconcile counts daily, and verify the hash chain on a schedule.

### Q40 [architect] Design a multi-step approval workflow engine.
tags: system-design, workflow-engine, state-machine, idempotency, outbox, escalation, basics

**Start here: the concepts**
- **Workflow engine:** software that moves a request (expense, purchase, access) through ordered steps until it is approved or rejected. It exists so the process lives in one place, not scattered across if-else code in many services.
- **Workflow definition vs instance:** the definition is the blueprint (steps, conditions, approvers). An instance is one real request travelling through it. Keeping them separate lets you change the blueprint without touching code.
- **State machine:** a model with a fixed set of states (e.g. SUBMITTED, MANAGER_REVIEW, APPROVED) and allowed transitions between them. Illegal moves, such as approving a rejected request, are impossible by design.
- **Idempotent action:** doing it twice has the same effect as doing it once. This matters because users double-click and networks retry.
- **Escalation timer:** a scheduled job that fires if nobody acts in time (remind, then reassign). Quartz is a Java scheduler that stores such jobs in a database.
- **Optimistic locking:** each row has a version number. An update succeeds only if the version is unchanged, so two simultaneous approvals cannot both win.
- **Outbox pattern:** write the business change and the "event to publish" in the same database transaction. A separate relay then publishes the event, so notifications are never lost or sent for rolled-back changes.
- **Camunda / Temporal:** ready-made engines. Camunda runs workflows drawn as BPMN diagrams. Temporal runs workflows written as code with durable, replayable state.

**The live scenario**
A procurement system handles about 20,000 requests a day (roughly 0.25 per second on average, perhaps 10 per second at peak). Approval rules are hard-coded, so each of the roughly 40 rule changes a quarter needs a deploy. One request sat for three days because the approver was on leave. A double-clicked "Approve" triggered a duplicate payment. Throughput is tiny; the real problems are correctness, changeability and time.

**What the interviewer is really checking**
Whether you separate definition from execution, protect against duplicates and races, handle time (escalations), and make a sensible build-vs-buy call.

**How I answer it**
1. **Clarify first:** serial or parallel approvals? Conditions (amount > 10k needs a director)? Delegation, rejection, resubmission, audit needs, expected volume. The answers decide whether a simple build is enough.
2. **Model definitions as data:** store steps, conditions and approvers in tables or JSON, and version them. Pin each instance to the version it started with, so a rule change does not alter requests mid-flight.
3. **One state machine per instance:** use Spring Statemachine or, more simply, an enum plus a transitions table (`from_state, event, guard, to_state`). Spring Statemachine's maintenance status should be checked before adopting it. The table approach is easy to test and audit.
4. **Persist state and history:** a current-state row with a version column (optimistic locking), plus an append-only history table (who, what, when, from, to). History gives the audit trail and debugging.
5. **Make actions idempotent:** each approval carries a unique action ID (or the check "instance is in state X at version N"). A retry or double-click then becomes a harmless no-op, not a second payment.
6. **Timers for escalation:** when an instance enters a waiting step, schedule a timer (Quartz with a database store, so timers survive restarts). On firing, re-check the state, then remind or reassign. Cancel or ignore the timer if the step already completed.
7. **Notifications via events:** each transition writes an event to an outbox, and a relay publishes it (for example to Kafka). Email and chat consumers react independently, so a slow mail server never blocks approvals.
8. **Build vs buy:** for a handful of linear flows, build the above. For parallel branches, sub-processes, long waits, versioned models or visual editing by business users, adopt Camunda or Temporal rather than rebuilding them poorly.

```sql
instance(id, definition_version, state, version)
history(instance_id, action_id UNIQUE, from_state, to_state, actor, at)
```

**Trade-offs and what can go wrong**
- Building yourself is cheap at first, but the edge cases (delegation, timers, migrations) accumulate and turn into a half-finished engine.
- Camunda and Temporal bring operational cost and a learning curve, plus lock-in to their model.
- Changing a definition mid-flight is dangerous without version pinning.
- Timers that fire late or twice need guards. Always re-check the state first.
- Outbox delivery is at-least-once, so consumers must also be idempotent.
- An approver who has left the company leaves requests stuck, so you need delegation and fallback rules.

**How I'd monitor it**
- Instances per state and age in each state; alert on the oldest pending.
- Escalation count and timer lag (scheduled time vs actual fire time).
- Rate of rejected duplicate actions and optimistic-lock conflicts.
- Outbox backlog size and age.
- Splunk searches by instance ID across transitions to trace one request end to end.

**Follow-ups to expect**
- *How do you handle parallel approvals (any 2 of 3)?* -> Keep a per-step approval counter or set in the same transaction as the transition, and move on when the rule is satisfied.
- *How do you scale it?* -> Stateless service nodes, with the database as the source of truth and partitioning by instance ID. Optimistic locking removes the need for a distributed lock.
- *Why Temporal over Camunda?* -> Temporal suits developers who want workflows as code. Camunda suits cases where analysts need to see and edit BPMN diagrams.

**60-second answer**
I would first clarify the flows, volumes and audit needs. Then I would store workflow definitions as versioned data and run each request as its own state machine, pinned to its definition version. Current state lives in a database row with optimistic locking, and every transition is appended to a history table for audit. Actions carry unique IDs so retries and double-clicks are harmless. Timers, for example in Quartz, handle reminders and escalation, and notifications go out as events through an outbox so none are lost. For a few simple flows I would build this myself. If I needed parallel branches, long waits or visual editing, I would use Camunda or Temporal instead of rebuilding them.

### Q41 [mid] How do you decide build vs buy vs open source?
tags: build-vs-buy, open-source, adr, total-cost-of-ownership, vendor-lock-in, architecture-decisions, basics

**Start here: the concepts**
- **Build:** your team writes and owns the software. You get exact fit and full control, and you also get every bug, upgrade and 3 a.m. page.
- **Buy:** you pay a vendor, usually through a licence or a SaaS subscription. You get speed and support, but you depend on the vendor's roadmap and prices.
- **Open source:** the code is public and you may use it under a licence. It costs nothing to download, but you still run, patch and upgrade it yourself, unless you pay a company for a managed version.
- **Total cost of ownership (TCO):** the full cost over the years, not just the first price tag. It is build cost + run cost (servers, on-call) + maintenance cost (upgrades, bug fixes, people).
- **Time to market:** how soon customers get the feature. A cheaper option that arrives 6 months late can cost more.
- **Vendor lock-in:** how painful it is to leave a product once you depend on it, for example because of proprietary APIs or data formats.
- **Licence:** the legal terms of use. Some open-source licences place obligations on you, and some projects change licence later.
- **Community health:** whether an open-source project has active maintainers, recent releases, fixed security issues and many users.
- **ADR (Architecture Decision Record):** a short document that records what you decided, why, and which options you rejected. It exists so people later do not have to guess or re-argue the decision.
- **Differentiator:** something customers choose you for, which competitors cannot easily copy.

**The live scenario**
A retail platform needs to send about 2M emails, SMS and push messages a day, which is roughly 23 per second on average and maybe 10x that during sales. A team of 6 proposed building their own notification service. Estimates: 3 engineers for 3 months to build, then about 0.5 engineer ongoing. Sending messages is not what makes the company special. A SaaS vendor could be live in 3 weeks, and an open-source engine would take about 6 weeks plus hosting. The team chose a vendor behind their own thin interface, and wrote an ADR. Six months later the vendor raised prices, and they could switch providers in days because only one adapter class touched the vendor's API.

**What the interviewer is really checking**
That you decide using explicit criteria and the real, long-term cost, not gut feeling or "we like writing code". They also want to see that you know open source is not free and that you write the decision down.

**How I answer it**
1. **Start with the business value of the capability.** Build only what differentiates the business. Your engineers' time is limited, so spend it where customers will notice. Generic needs like email, auth or payments should usually be bought or reused.
2. **Write down the requirements and check fit.** List the must-haves (volume, latency, compliance) and the nice-to-haves. A product that meets 70% of the must-haves means workarounds forever, so check this before comparing prices.
3. **Compare TCO over about 3 years, not the sticker price.** Add build + run + maintain for each option. Include people's time and on-call, because maintenance is usually the biggest hidden cost.
4. **Weigh time to market.** Ask what a delay costs: lost revenue or a missed deadline. A faster option is worth more when the window is short.
5. **Assess vendor lock-in and an exit plan.** Ask how you would leave and how long it would take. Reduce the risk by hiding the product behind your own interface (Adapter pattern) and keeping your data exportable.
6. **Check security and licensing.** Look at certifications, how fast vulnerabilities are fixed and where data is stored. Have legal read the licence terms, including whether it may change.
7. **Check community health for open source.** Look at the date of the last release, the number of active maintainers, how issues are handled, and whether a company backs it. A dead project becomes your project.
8. **Match the choice to team skills.** A great tool nobody on the team can operate is a risk. Count the learning time as a cost.
9. **Record it in an ADR.** Capture the context, the options, the decision, the consequences and a review date, so the decision can be revisited when facts change.

**Trade-offs and what can go wrong**
- Build: underestimated scope, a bus factor of one person, and "temporary" code that lives for ten years.
- Buy: price rises, outages you cannot fix, hard limits on features, and data-exit pain.
- Open source: hidden operating cost, abandoned projects, licence changes, and slow security patching if nobody owns upgrades.
- Common mistakes: comparing only the initial cost, building because it is more fun (not-invented-here), and skipping the exit plan.

**How I'd monitor it**
- Actual vs estimated cost and effort, reviewed quarterly.
- Vendor SLA vs the uptime you measure, plus incident counts linked to the product.
- Dependency and CVE scans (for example, a software composition analysis tool) and how long patches take to roll out.
- Open-source health: release cadence, and how far behind the latest version you are.
- A calendar reminder to review each ADR, and a check that the exit path still works.

**Follow-ups to expect**
- *When is building the right call?* -> When the capability is a differentiator, no product fits the must-haves, or data control and compliance rule out outside options.
- *How do you limit lock-in if you buy?* -> Put an adapter or interface in front of the vendor, keep data exportable, and prefer standard protocols.
- *Is open source really free?* -> No. You pay with people's time for running, patching and upgrading, and the licence terms still matter.

**60-second answer**
I first ask whether the capability differentiates the business. If it does, I lean towards building, and if it is generic, I buy or reuse. Then I compare the total cost over about three years: build, run and maintain, not just the price. I also look at time to market, how well it fits the requirements, lock-in and the exit plan, security and licensing, community health for open source, and whether my team can operate it. I hide any external product behind my own interface so I can swap it later. Finally I write an ADR with the options and reasons, and set a review date, so the decision can be revisited when facts change.

### Q42 [mid] What is an Architecture Decision Record (ADR)?
tags: adr, architecture, documentation, decision-making, git, team-process, basics

**Start here: the concepts**
- **Architecture decision:** a choice that is costly to reverse and shapes the system, such as picking Kafka over RabbitMQ, a database, or a module boundary.
- **ADR (Architecture Decision Record):** a short document, usually one page, that records one such decision and why it was made. Code shows *what* the system does, but not *why* it was built that way. ADRs exist to capture that "why" before people forget it or leave.
- **Context:** the situation and constraints when you decided, such as traffic, deadlines, team skills and budget.
- **Options considered:** the real alternatives, each with its pros and cons, including the ones you rejected.
- **Decision:** the choice made, in one or two clear sentences.
- **Consequences:** what becomes easier and harder because of the choice, including the downsides you accept.
- **Status:** a label such as Proposed, Accepted, Deprecated or Superseded.
- **Immutable:** once accepted, you do not rewrite the reasoning. If things change, you write a new ADR, and the old one's status becomes "Superseded by ADR-0042". The old text stays, so the history is honest.
- **Stored in the repo:** ADRs live as Markdown files next to the code, usually in a `docs/adr/` folder. They are reviewed through pull requests and versioned with the code.

**The live scenario**
A payments team of 8 runs about 2,000 requests per second. Eighteen months ago they chose Kafka over a database-backed queue. A new engineer joins and proposes, "Let's replace Kafka with a DB table, it's simpler." Nobody remembers why Kafka was chosen. The team spends two weeks of meetings re-debating it and nearly migrates. Then someone finds ADR-0007: the context was a peak of 5,000 events per second, a need to replay events for audits, and three consumers reading the same stream. The DB queue failed all three. The debate ends in 20 minutes. The team then notes that volume is now much lower and writes ADR-0023 to revisit the decision with current numbers.

**What the interviewer is really checking**
Whether you understand that decisions need recorded reasoning, not just recorded results. They also want to know whether you have a lightweight, practical habit for it, not a heavy documentation process.

**How I answer it**
1. **Define it in one sentence.** An ADR is a short record of one architecture decision: context, options, decision, consequences. A small, simple definition shows you understand the purpose before the format.
2. **Name the four parts and say why each matters.** Context shows the constraints, so a future reader can tell whether they still apply. Options show what was rejected, which stops people proposing the same idea again. The decision is the outcome. Consequences show you knew the costs up front.
3. **Say where it lives.** It goes in the repo, one file per decision, numbered, and reviewed by pull request. Docs kept in a wiki drift away from the code and get lost. In the repo, the review is also where the team discusses the decision.
4. **Explain immutability.** You never edit the reasoning of an accepted ADR. You write a new one that supersedes it and update only the status line. That way you can see *how* thinking changed, and you never rewrite history to look smarter.
5. **Say what it gives the team.** New joiners get the "why" without interrupting seniors, repeated debates are avoided, and the decision gets thought through before it is made. This is the real meaning of "leadership maturity": decisions are explicit and open to challenge.

```
# ADR-0007: Use Kafka for payment events
Status: Accepted | Context: ... | Decision: ... | Consequences: ...
```

**Trade-offs and what can go wrong**
- Writing ADRs takes time, so keep them to one page and write them only for significant decisions, not every library choice.
- ADRs written months later are guesses. Write them while deciding.
- A stale "Accepted" ADR that has actually been abandoned misleads people. Always mark it Superseded.
- Hiding the rejected options or the downsides makes an ADR a sales pitch instead of a record.
- Without team buy-in, the folder stays empty.

**How I'd monitor it**
- Check in code reviews that big design changes link to an ADR.
- Check that the number of ADRs grows steadily and that none sit in "Proposed" for weeks.
- Run a CI check or a template for the required headings and status values.
- Run a quarterly review of the ADR list for decisions whose context has changed.
- Ask new joiners whether the ADRs helped them.

**Follow-ups to expect**
- *Which decisions deserve an ADR?* -> Ones that are expensive to reverse or affect several teams: datastore, messaging, service boundaries, security approach.
- *What if an ADR turns out wrong?* -> Don't edit it. Write a new ADR that supersedes it, explain what changed, and link both.
- *ADR vs design document?* -> A design doc describes a whole solution. An ADR records one decision and its reasoning, and is much shorter.

**60-second answer**
An Architecture Decision Record is a short document about one important technical decision. It has four parts: the context and constraints, the options we considered, the decision, and its consequences. We keep it in the repo as a Markdown file and review it in a pull request. Once accepted, we don't rewrite it. If we change course, we write a new ADR and mark the old one as superseded. The value is that new team members learn why something was built a certain way, and we don't repeat the same debates. It also forces us to think through the trade-offs before we commit. I'd use it only for decisions that are costly to reverse, and keep each one to a page.

### Q43 [mid] Is Spring MVC a design pattern? If yes, what is it?
tags: spring-mvc, mvc, front-controller, dispatcherservlet, design-patterns, spring-boot, basics

**Start here: the concepts**
- **Design pattern**: a named, reusable solution to a problem that keeps recurring in code (for example Strategy, Adapter). It lives at the level of a few classes.
- **Architectural pattern**: the same idea at a bigger scale. It describes how a whole application or layer is organised. MVC is one.
- **MVC (Model-View-Controller)**: split the presentation layer into three roles. The *Model* is the data to show. The *View* is how it is rendered (HTML page, JSON). The *Controller* takes the request, calls business code and picks the model and view. It exists so UI changes do not force business-logic changes.
- **Spring MVC**: the Spring Framework web module (servlet stack) that implements MVC. It is a framework, not a pattern.
- **Front Controller**: one single entry point receives every request and delegates it. In Spring MVC this is `DispatcherServlet`, so common concerns are handled in one place.
- **HandlerMapping**: decides which controller method serves a URL. Swappable implementations make it a **Strategy**.
- **Interceptor (`HandlerInterceptor`)**: code that runs before and after a controller. Several in a row form a **Chain of Responsibility**.
- **HandlerAdapter**: the piece that actually calls the chosen controller method and fills its arguments.
- **ViewResolver**: turns a view name such as `"orders"` into a real page (for example a template).
- **HttpMessageConverter**: converts a Java object to JSON (or back) for REST APIs.

**The live scenario**
An orders service handles about 300 requests/second with 40 controllers. Early on, each developer copied token-checking and request-timing code into every controller. One controller missed the check and a security review flagged it. The team moved the logic into one interceptor, so every request passes through it. Separately, a new developer wrote `@Controller` (not `@RestController`) and returned an object. Spring looked for a *view* with that name and the API returned errors instead of JSON. Both problems come from not knowing how the request flows through Spring MVC.

**What the interviewer is really checking**
Can you tell an architectural pattern (MVC) from the framework that implements it (Spring MVC), and name the smaller patterns inside it? Do you understand the real request flow, not just the letters M-V-C?

**How I answer it**
1. **Say yes, with a precision.** MVC is an *architectural* pattern, not a GoF design pattern. "Spring MVC" is the framework module that implements it. This shows you know the difference between the idea and the tool.
2. **Name the Front Controller.** `DispatcherServlet` receives every request. One entry point means cross-cutting work (routing, error handling) is done once.
3. **Walk the flow.**
   - `HandlerMapping` finds the handler, together with its interceptors.
   - Interceptors run their `preHandle` step.
   - A `HandlerAdapter` calls the `@Controller` method.
   - The controller returns a model and a view name.
   - A `ViewResolver` finds the view and renders it.
   - Interceptors then run their post-processing.

   Mention that servlet *Filters* run earlier, before `DispatcherServlet`.
4. **Link each step to a pattern.** `HandlerMapping` is Strategy, the interceptor list is Chain of Responsibility, and `DispatcherServlet` is Front Controller. This answers the "which patterns?" follow-up before it is asked.
5. **Cover REST.** With `@RestController` (or `@ResponseBody`) there is no view step. The return value is written by an `HttpMessageConverter` (Jackson for JSON), because APIs return data, not pages.

```java
@RestController  // = @Controller + @ResponseBody: skips ViewResolver
class OrderApi { @GetMapping("/orders/{id}") Order get(@PathVariable long id) {...} }
```

**Trade-offs and what can go wrong**
- Spring MVC is a loose interpretation of MVC. In REST there is effectively no View, and the "model" is often just a DTO.
- Using `@Controller` where `@RestController` was meant gives view-resolution errors.
- Heavy interceptors add latency to every request.
- Business logic inside controllers defeats the layering that MVC is meant to give.
- This is the blocking servlet stack. Spring WebFlux uses a different, reactive model.

**How I'd monitor it**
- Spring Boot Actuator `http.server.requests` metric: latency and error counts per URI.
- Log interceptor timings, and search Splunk for slow endpoints or 404/500 spikes after a deploy.
- Alert on p95 latency and 5xx rate per endpoint.

**Follow-ups to expect**
- *Difference between a Filter and an Interceptor?* -> Filters are part of the Servlet spec and run before `DispatcherServlet`. Interceptors are Spring MVC and run around the handler call, with access to the handler.
- *`@Controller` vs `@RestController`?* -> `@RestController` adds `@ResponseBody`, so return values go through `HttpMessageConverter`s instead of view resolution.
- *Is Spring MVC the same as Spring Boot?* -> No. Boot auto-configures Spring MVC and an embedded server. MVC is the web framework.

**60-second answer**
MVC is an architectural pattern that separates Model, View and Controller in the presentation layer. Spring MVC is the framework that implements it. Every request enters through `DispatcherServlet`, which is the Front Controller pattern. A `HandlerMapping` (Strategy) picks the controller, interceptors (Chain of Responsibility) run around it, and a `HandlerAdapter` calls the method. For web pages, a `ViewResolver` then renders the view. In a REST API with `@RestController` there is no view step, and an `HttpMessageConverter` writes JSON instead. So Spring MVC is not a design pattern itself. It is a framework built from several patterns working together.

### Q44 [mid] Which pattern handles boilerplate like cleanly closing connections?
tags: design-patterns, template-method, execute-around, jdbctemplate, try-with-resources, resource-management, basics

**Start here: the concepts**
- **Boilerplate:** code you must write the same way every time, such as "get a connection, use it, close it, handle errors". It is easy to get wrong because it is repetitive.
- **Resource leak:** a connection, statement or file is opened but never closed. Connections come from a limited pool, so leaks eventually leave nobody able to get one.
- **Connection pool:** a fixed set of ready database connections that threads borrow. "Closing" a pooled connection returns it to the pool. If you skip that step, the pool shrinks until it is empty.
- **Template Method pattern:** a fixed skeleton of steps (acquire, use, release, handle errors) with one step left open for the caller to fill in. The classic form uses inheritance (a subclass overrides a method).
- **Callback / execute-around form:** instead of subclassing, you pass the varying step in as a lambda or small object. The template runs "before" code, calls your code, then runs "after" code, even if your code fails. `JdbcTemplate` works this way.
- **try-with-resources (Java 7+):** the language feature for the same job. Any object implementing `AutoCloseable` declared in the `try (...)` header is closed automatically, in reverse order, even on exceptions.
- **Exception translation:** converting low-level checked errors (`SQLException`) into a cleaner, unchecked hierarchy (Spring's `DataAccessException`) so callers are not tied to one database API.

**The live scenario**
An order service handles about 400 requests per second against a pool of 20 connections. One developer wrote a rarely used "export" query by hand and returned early on an error path before calling `close()`. Nothing failed in testing. In production, each failed export leaked one connection. After a few hundred failures over a day, the pool hit 20 of 20 in use. Every endpoint then waited 30 seconds for a connection and timed out, and the whole service looked down. The fix was to move all data access to `JdbcTemplate` and try-with-resources, so no code path could forget the release.

**What the interviewer is really checking**
Whether you can name the pattern that removes repeated setup/cleanup code, explain why it prevents leaks, and tell it apart from similar patterns (Strategy, Decorator). Mid-level candidates should also know the modern Java equivalent.

**How I answer it**
1. **Name it: Template Method in execute-around/callback form.** The reason is that the template owns the lifecycle (acquire, use, release, translate exceptions), and the caller supplies only the part that varies.
2. **Give the real example.** `jdbcTemplate.query(sql, rowMapper)`: you write only "how to turn one row into an object". The template opens the connection, runs the statement, iterates the `ResultSet`, closes everything in a `finally`, and translates `SQLException`. Your code never touches `Connection`, so it cannot forget to close it.
3. **Explain why this beats copying boilerplate.** Cleanup is written and tested once, in one place, instead of being repeated and possibly broken in 200 methods.
4. **Give the plain-Java equivalent.** When there is no template class, use try-with-resources. The compiler generates the close calls:
```java
try (Connection c = ds.getConnection();
     PreparedStatement ps = c.prepareStatement(sql)) { /* use */ }
```
5. **Say what it is not.** Strategy is about swapping interchangeable algorithms, and Decorator is about wrapping an object to add behaviour. The callback form looks structurally like Strategy because you pass in behaviour, but the intent differs. Here the point is a fixed lifecycle around a variable step, not choosing between algorithms.

**Trade-offs and what can go wrong**
- Classic inheritance-based Template Method ties you to a base class. The callback form avoids that, which is why Spring uses it.
- "A leak is impossible" is too strong. It is impossible inside the template's methods, but you can still leak by calling `DataSource.getConnection()` yourself, or by returning a lazily-read stream or cursor that outlives the template call.
- Long work inside the callback (remote calls, big loops) still holds the connection for its whole duration, even though it is closed correctly afterwards.
- With try-with-resources, if both the body and `close()` throw, the body's exception wins and the close failure is attached as a *suppressed* exception, so check it when debugging.

**How I'd monitor it**
- Pool metrics (HikariCP via Micrometer/Actuator): active, idle and pending connections, and connection acquire time. Active stuck at the maximum with pending above zero signals a leak.
- HikariCP's leak detection threshold logs a stack trace for a connection held too long.
- Splunk: search for connection timeout errors ("Connection is not available, request timed out") and alert on their rate.
- Code review and static analysis rules that flag `getConnection()` outside a template or try-with-resources.

**Follow-ups to expect**
- *Why isn't this Strategy?* -> Strategy chooses between interchangeable algorithms. Here a fixed lifecycle wraps one variable step. The callback shape is similar, but the intent is cleanup and control flow.
- *What does try-with-resources require?* -> The resource must implement `AutoCloseable`. Resources close in reverse order of declaration, and close exceptions are added as suppressed.
- *Where else does Spring use this idea?* -> `TransactionTemplate`, `RestTemplate`, `JmsTemplate` and `KafkaTemplate` all hide setup, cleanup and error handling around your specific logic.

**60-second answer**
The pattern is Template Method, in its callback or execute-around form. The template owns the fixed steps: acquire the resource, run your code, release it, and translate exceptions. You supply only the part that varies. `JdbcTemplate.query(sql, rowMapper)` is the example. I give it a SQL string and a row mapper, and it opens and closes the connection and statement for me, so I can't leak through that path. In plain Java I get the same effect with try-with-resources on `AutoCloseable` objects. It is not Strategy, which swaps algorithms, and not Decorator, which adds behaviour. I'd still watch pool metrics, because holding a connection too long or bypassing the template can exhaust the pool.

### Q45 [mid] Which design patterns are used inside the JDK, Hibernate and Spring?
tags: design-patterns, jdk, hibernate, spring, proxy, factory, strategy, basics

**Start here: the concepts**
- **Design pattern**: a named, reusable solution to a problem that keeps recurring in code. The name lets developers say "use a Strategy" instead of explaining a whole design.
- **Singleton**: only one instance of a class exists, e.g. `Runtime.getRuntime()`. It exists for things that represent one shared resource.
- **Factory**: a method that creates objects so callers don't call `new` directly, e.g. `Calendar.getInstance()` and `List.of(...)`. The factory can choose the concrete class.
- **Flyweight**: share small, immutable objects instead of creating copies. `Integer.valueOf` caches values from -128 to 127 to save memory.
- **Decorator**: wraps an object, implements the same interface and adds behaviour. `BufferedReader` adds buffering to another `Reader`. `Collections.unmodifiableList` also wraps a list, but it removes behaviour (writes), so it is often called a wrapper or proxy.
- **Adapter**: converts one interface into another. `Arrays.asList` presents an array as a `List`. `InputStreamReader` turns bytes into characters.
- **Iterator**: walks a collection without exposing its internals.
- **Strategy**: pass in interchangeable behaviour. `Comparator` is the sorting rule you plug into `sort`.
- **Observer**: listeners get notified when something changes, e.g. `PropertyChangeListener`.
- **Template Method**: a base class fixes the skeleton and subclasses fill in steps. `AbstractList` needs only `get` and `size` from you.
- **Builder**: builds a complex object step by step, e.g. `HttpClient.newBuilder()`. `StringBuilder` is a mutable string builder, but it is not the strict GoF Builder.
- **Proxy**: a stand-in object that controls access to the real one. Hibernate and Spring both rely on it.
- **Unit of Work / Identity Map**: Unit of Work tracks changes and writes them together. Identity Map ensures one row maps to one in-memory object per session. Hibernate's persistence context does both.

**The live scenario**
An order service handles 200 requests/second. After a release, p95 latency on `GET /orders` jumped from 40 ms to 900 ms. The developer had loaded 50 orders, and each order's `items` collection was lazy. Hibernate returned **proxies**, and touching each one fired a separate SQL query: 1 + 50 queries per request, about 10,000 queries/second. The team only found it because they knew lazy loading is a Proxy. The fix was a fetch join. The same week, another developer's `==` comparison on `Integer` worked for 100 but failed for 1000, which is the Flyweight cache.

**What the interviewer is really checking**
That you can connect pattern names to real classes you use daily, and that you understand the behaviour each pattern causes (proxy surprises, caching limits). Reciting a list is not enough.

**How I answer it**
1. **Start with the JDK**, because it is the easiest to see. Group by purpose. Creation: Singleton, Factory, Builder, Flyweight. Structure: Decorator, Adapter. Behaviour: Iterator, Strategy, Observer, Template Method. Grouping shows you understand why the patterns exist.
2. **Be precise about the loose ones.** `StringBuilder` is not a textbook Builder. `unmodifiableList` is a wrapper, closer to Proxy/Decorator.
3. **Move to Hibernate.** `SessionFactory` is a Factory: expensive, built once, creates cheap `Session`s. Lazy loading is a Proxy (a generated subclass loads data on first access). The persistence context (the `Session`) is Unit of Work plus Identity Map: it tracks dirty entities and flushes at commit, and it returns the same object for the same id. **Correction:** Hibernate itself is not a Template or DAO. The DAO is a pattern you write on top, and Template came from Spring's old `HibernateTemplate`, now legacy.
4. **Then Spring**, since the stored answer only said "see Q24":
   - Singleton scope: one bean per container, not per JVM.
   - Factory: `BeanFactory` and `ApplicationContext`.
   - Proxy: AOP, `@Transactional`, `@Async`.
   - Template Method/callback: `JdbcTemplate`, `RestTemplate`.
   - Observer: `ApplicationEvent` and `@EventListener`.
   - Front Controller: `DispatcherServlet`.
   - Adapter: `HandlerAdapter`.
   - Dependency Injection is the core idea, and it is not a GoF pattern.
5. **Close with a consequence**, e.g. proxies mean self-invocation bypasses `@Transactional`.

**Trade-offs and what can go wrong**
- Proxies hide cost: lazy loading causes N+1 queries or `LazyInitializationException` outside a session.
- Spring proxies don't apply on self-invocation, `private` methods or `final` classes.
- The Flyweight cache means `Integer == Integer` is true only for small values. Always use `equals`.
- Spring singletons are shared across threads, so mutable fields cause race conditions.
- Don't force patterns where a lambda or a plain method is enough.

**How I'd monitor it**
- Enable Hibernate statistics (`hibernate.generate_statistics`) and watch the query count per request.
- Search Splunk for the same `select ... from order_item where order_id=?` repeated within one trace id.
- Track p95 latency and Hikari pool usage (Micrometer/Actuator).
- Use the database slow-query log and query-per-second graphs.

**Follow-ups to expect**
- *Is Spring's singleton the same as the GoF Singleton?* -> No. Spring creates one instance per container, so two contexts have two instances. GoF enforces one per classloader in the class itself.
- *How does Spring create the proxy for `@Transactional`?* -> A JDK dynamic proxy if the bean has an interface, otherwise a CGLIB subclass. The proxy opens the transaction, calls your method, then commits or rolls back.
- *Decorator vs Proxy?* -> Decorator adds behaviour. Proxy controls access, such as laziness, security or transactions. The structure looks alike but the intent differs.

**60-second answer**
The JDK is full of patterns. Singleton is `Runtime.getRuntime`, Factory is `List.of` and `Calendar.getInstance`, Flyweight is the `Integer.valueOf` cache, Decorator is `BufferedReader`, Adapter is `Arrays.asList`, Strategy is `Comparator`, Observer is `PropertyChangeListener`, and Template Method is `AbstractList`. Hibernate uses a Factory in `SessionFactory`, a Proxy for lazy loading, and Unit of Work plus Identity Map in the persistence context. Spring uses Factory in `ApplicationContext`, Proxy for AOP and `@Transactional`, Template Method in `JdbcTemplate`, Observer in application events, and
