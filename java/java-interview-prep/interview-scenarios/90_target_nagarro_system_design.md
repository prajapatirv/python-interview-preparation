---
id: target-nagarro-system-design
title: Target company, Nagarro (1/3): system design round, 8 classic prompts
stack: java
skill: architecture
---
Part of the **target-company section** (hub: `../target-companies/README.md`, section "Nagarro").
These are the eight design prompts Nagarro candidates most often report for mid and senior backend roles.
The round is usually 45-60 minutes, and the interviewer scores **clarity of assumptions, scalability, explained
trade-offs and practical fluency** (Spring Boot, Docker, Kubernetes) more than a "perfect" diagram.

Use the same five-step skeleton for every prompt, out loud:

```text
1. CLARIFY   functional scope, users, read/write ratio, latency target, consistency needs  (3-5 min)
2. NUMBERS   QPS, storage per year, peak factor                                          (2-3 min)
3. HLD       client -> gateway -> services -> data stores -> async pipeline              (10 min)
4. DEEP DIVE the 2-3 hard parts the interviewer picks (collisions, ordering, payments...)  (20 min)
5. WRAP UP   trade-offs, failure modes, monitoring, how it evolves                        (5 min)
```

Every answer has a **120-second** point-by-point version (*How I answer it*) and a **60-second answer**.
In the real round you expand the 120-second points onto the whiteboard.

### Q1 [senior] Design a URL shortener like Bitly, with collision handling and click analytics
tags: url-shortener, base62, hashing, collision, key-generation, cache, analytics, kafka, nagarro, system-design

**Start here: the concepts**
- A URL shortener maps a **short code** (for example `aZ3k9Q`) to a long URL and redirects with HTTP 301 or 302.
- **Base62** (a-z, A-Z, 0-9) gives 62^7 = about 3.5 trillion codes with 7 characters.
- A **collision** happens when two long URLs produce the same short code.
- The system is **read-heavy**: one link is created once and clicked thousands of times.

**The live scenario (functional requirement)**
*FR: "Marketing creates short links for campaigns. A link must redirect in under 50 ms, and the team wants clicks per
link per day, by country and device."* Assume 100 million new links per month and a 100:1 read/write ratio.

**What the interviewer is really checking**
Whether you do the numbers, choose a key-generation strategy that cannot collide (or detects it cheaply), keep the
redirect path fast with a cache, and keep analytics **off** the redirect path.

**How I answer it** (120-second answer, point by point)
1. **Clarify:** custom aliases? expiry? edit after creation? 301 (cached by the browser, fewer analytics) or 302 (every click reaches us)? For analytics I pick **302**.
2. **Numbers:** 100M writes/month = about 40 writes/s; reads 100x = about 4,000/s average, plan for 20,000/s peak. 100M x 12 x 5 years x ~500 bytes = about 3 TB. Small data, high read rate.
3. **API:** `POST /links {longUrl, alias?, expiresAt?}` returns the code; `GET /{code}` returns 302 with `Location`.
4. **Key generation, three options and my choice:**
   - *Hash the URL* (MD5 then the first 7 base62 characters): same URL gives the same code, but collisions must be checked and retried with a salt.
   - *Random 7 characters*: simple, needs an existence check, and collisions grow as the table fills.
   - **Counter + base62 (my choice):** a unique 64-bit id from a range allocator (each app instance leases a block of 10,000 ids from the database or ZooKeeper) is encoded to base62. **No collisions by construction**, no coordination per request. I shuffle the id bits so codes are not guessable in sequence.
5. **Custom alias:** an insert with a **unique constraint** on `code`. A conflict returns 409; that is the only collision path left.
6. **Storage:** a key-value lookup by code: DynamoDB/Cassandra, or PostgreSQL with a primary key at this size. Row: code, long URL, owner, created, expires.
7. **Read path:** gateway -> redirect service -> **Redis cache** (LRU, hit rate above 90% because traffic is skewed to hot links) -> database on a miss. A CDN can cache the hottest links at the edge.
8. **Analytics:** the redirect service publishes a click event (code, timestamp, IP-derived country, user agent) to **Kafka asynchronously** and returns immediately. A stream job aggregates per code/day/country into an OLAP store (ClickHouse or Druid). A redirect never waits for analytics.
9. **Expiry and abuse:** TTL on rows plus a cleanup job; rate limiting per API key on creation; a malicious-URL check before storing.

**Trade-offs and what can go wrong**
- 301 is cheaper (browsers cache it) but you lose most click data. 302 costs more traffic but gives analytics.
- Hash-based codes deduplicate the same URL but need a collision loop. Counter-based codes never collide but give each submission a new code (fine, and per-user links are often wanted anyway).
- If Kafka is down, buffer click events locally with a bounded queue and drop the oldest. Analytics may lose a few clicks; redirects must never fail because of them.
- Hot-key risk: one viral link. The cache plus the CDN absorb it; never let it fall through to the database.

**How I'd monitor it**
Redirect p99 latency, cache hit ratio, 404 rate (bad or expired codes), Kafka producer error rate, consumer lag of the
analytics job, and the id-range allocator's remaining blocks.

**Numbers I quote**
- 62^7 = 3.5 trillion codes; 62^6 = 56 billion.
- About 40 writes/s and 4,000 reads/s average; 3 TB over 5 years.

**Follow-ups to expect**
- *Two users shorten the same URL, same code or different?* -> Different with the counter approach; if dedup is required, add a lookup index on a hash of the long URL.
- *How do you make codes non-sequential?* -> Encode a bit-shuffled or Feistel-permuted id, so neighbours do not look alike.
- *How do you scale to 1 million redirects per second?* -> CDN at the edge, more cache replicas, read replicas or a sharded KV store by code.

**60-second answer**
"I'd first confirm the numbers: about 40 creates a second and 4,000 redirects a second, around 3 TB over five years, so it's
a read-heavy key-value problem. To avoid collisions I generate ids from leased counter ranges and base62-encode them to
seven characters, which gives 3.5 trillion codes and no collision checks. Custom aliases go through a unique constraint
and return 409 on conflict. Redirects go gateway, service, Redis, then the database on a miss, and return a 302 so we can
count clicks. Each click goes to Kafka asynchronously and a stream job aggregates by link, day and country into an OLAP
store, so analytics can never slow a redirect. I'd watch p99 redirect latency, cache hit ratio and consumer lag."

### Q2 [senior] Design a real-time chat system with delivery guarantees and offline delivery
tags: chat, websocket, presence, message-ordering, delivery-receipts, offline, kafka, cassandra, nagarro, system-design

**Start here: the concepts**
- A **WebSocket** is a long-lived two-way connection, so the server can push messages without the client polling.
- **At-least-once delivery + idempotent client** = the client may receive a message twice and ignores the duplicate by message id.
- **Offline delivery** means storing the message and delivering it (plus a push notification) when the user reconnects.

**The live scenario (functional requirement)**
*FR: "Support 1-to-1 and group chat for 10 million daily users. Messages appear in under 300 ms when both users are
online, survive the receiver being offline, and show sent / delivered / read ticks."*

**What the interviewer is really checking**
Connection management at scale, how a message finds the server where the receiver is connected, ordering within a
conversation, durable storage, and the difference between delivery and read receipts.

**How I answer it** (120-second answer, point by point)
1. **Clarify:** 1-to-1 and groups up to 500? media? end-to-end encryption? history kept how long?
2. **Numbers:** 10M DAU x 40 messages = 400M messages/day = about 5,000/s average, 25,000/s peak; at peak 2-3M concurrent connections. One chat server holds about 50k-100k connections, so roughly 30-60 servers.
3. **Connection layer:** clients connect over WebSocket through an L4 load balancer to stateless **chat gateway** nodes. A **session registry** in Redis maps `userId -> gatewayNode` with a TTL refreshed by heartbeats (this also gives presence).
4. **Send path:** client sends `{clientMsgId, conversationId, body}`. The gateway calls the message service, which **persists first** (Cassandra, partition key `conversationId`, clustering key a time-ordered id such as a Snowflake id) and only then acknowledges "sent" to the sender.
5. **Fan-out:** the message service publishes to Kafka, keyed by `conversationId` so ordering per conversation holds. A delivery worker looks up each recipient in the session registry and forwards to their gateway node. If the recipient is offline, it triggers a **push notification** (APNs/FCM) instead.
6. **Offline and reconnect:** each device keeps a `lastSeenMessageId` per conversation. On reconnect it asks "give me everything after X". The store is the source of truth; the live push is only an optimisation.
7. **Receipts:** "delivered" when the recipient device acks; "read" when the conversation is opened. Both are small events through the same pipeline, batched for groups.
8. **Groups:** small groups fan out on write; very large groups/channels fan out on read (clients pull), to avoid writing 100k copies.
9. **Idempotency:** `clientMsgId` dedupes retries from flaky mobile networks.

**Trade-offs and what can go wrong**
- Persist-before-ack adds a few milliseconds but means "sent" is never a lie.
- Ordering is guaranteed per conversation, not globally; that is all users need.
- A gateway node crash drops many connections at once: clients reconnect with jitter (exponential backoff) to avoid a thundering herd, then sync from `lastSeenMessageId`.
- Presence is eventually consistent; accept a few seconds of staleness.

**How I'd monitor it**
Concurrent connections per node, message end-to-end latency (send to deliver) p99, Kafka consumer lag of delivery
workers, push-notification failure rate, reconnect storms (connections per second), and undelivered-message backlog.

**Follow-ups to expect**
- *Why not a database poll?* -> Millions of clients polling every second wastes capacity and adds latency; push over WebSocket is cheaper.
- *How do you guarantee order in a group?* -> One Kafka partition per conversation key and a time-ordered id assigned by the message service.
- *How do you handle multiple devices?* -> Register every device session; deliver to all; track `lastSeen` per device.

**60-second answer**
"With 10 million daily users I'd plan for about 25,000 messages a second and 2-3 million open connections. Clients hold a
WebSocket to stateless gateway nodes, and Redis maps each user to their node, which also gives presence. On send, the
message service persists to Cassandra, partitioned by conversation with a time-ordered id, and only then acks 'sent'.
It publishes to Kafka keyed by conversation, so order holds, and delivery workers push to the receiver's gateway, or send
a push notification if they're offline. On reconnect, the device syncs everything after its last-seen id, so the store is
the truth and the push is just an optimisation. Client message ids make retries idempotent, and I'd watch end-to-end
latency and consumer lag."

### Q3 [senior] Design an e-commerce checkout flow: inventory, payment, order tracking and fault tolerance
tags: checkout, inventory-reservation, payment, saga, outbox, idempotency, order-state-machine, nagarro, system-design

**Start here: the concepts**
- **Reservation** = hold stock for a few minutes while the customer pays, instead of deducting it immediately.
- A **saga** is a sequence of local transactions across services, each with a **compensating** action (release stock, refund) if a later step fails.
- The **transactional outbox** writes the business change and the event in one database transaction, so an event is never lost.

**The live scenario (functional requirement)**
*FR: "During a flash sale, 50,000 users check out in 10 minutes. We must never oversell, never charge twice, and the
customer must see the order status at every step."*

**What the interviewer is really checking**
That you avoid a distributed transaction (2PC), handle the "money deducted but order failed" case, make payments
idempotent, and protect inventory from overselling under concurrency.

**How I answer it** (120-second answer, point by point)
1. **Services:** cart, order, inventory, payment (wraps the payment gateway), notification. Each owns its data.
2. **Order state machine:** `CREATED -> STOCK_RESERVED -> PAYMENT_PENDING -> PAID -> CONFIRMED -> SHIPPED`, with `CANCELLED` / `PAYMENT_FAILED` exits. Every transition is an event; the UI shows the state.
3. **Step 1, create order:** `POST /orders` with an **Idempotency-Key** header. Same key = same order returned, so double-clicks do not create two orders.
4. **Step 2, reserve stock:** inventory runs `UPDATE stock SET available = available - :q WHERE sku = :s AND available >= :q`. One atomic conditional update; zero rows updated = out of stock. No oversell, no long locks. The reservation expires in 10 minutes.
5. **Step 3, payment:** the payment service calls the gateway with the **order id as the idempotency key**. A timeout is "unknown", not "failed": we query the gateway or wait for its webhook before deciding.
6. **Saga orchestration:** an orchestrator in the order service drives the steps. Payment fails -> release the reservation -> order `PAYMENT_FAILED`. Payment succeeds but confirmation fails -> retry (it is idempotent); if it is permanently impossible, refund as compensation.
7. **Reliable events:** every service writes state + event to an **outbox** table in one transaction; a relay (Debezium or a poller) publishes to Kafka. Consumers are idempotent by event id.
8. **Flash-sale protection:** a queue/virtual waiting room in front of checkout, rate limiting per user, inventory counters pre-loaded in Redis for a fast "sold out" check before the database.
9. **Reconciliation:** a nightly job compares payment-gateway settlements with orders and flags mismatches.

**Trade-offs and what can go wrong**
- Orchestration is easier to reason about and monitor; choreography (services react to events) has less coupling but the flow is hidden across services. For checkout I prefer orchestration.
- A reservation TTL that is too short frustrates slow payers; too long locks stock that will never sell. 10-15 minutes is typical.
- The classic bug: treating a payment timeout as failure and releasing stock while the customer was actually charged. Unknown must stay unknown until confirmed.

**How I'd monitor it**
Orders stuck in one state longer than N minutes (the most useful alert), payment success rate by gateway, compensations
per hour, oversell count (must be zero), outbox relay lag, and checkout p99 latency.

**Follow-ups to expect**
- *Why not 2PC?* -> The payment gateway does not take part in XA transactions, and 2PC holds locks across slow network calls.
- *Money deducted but order creation failed?* -> The saga sees a successful payment without a confirmed order: retry confirmation; if impossible, issue an automatic refund and notify.
- *How do you prevent double charge?* -> Idempotency key per order at the gateway, plus a unique constraint on `(orderId)` in the payments table.

**60-second answer**
"I split checkout into order, inventory and payment services and drive it with an orchestrated saga instead of a
distributed transaction. The order has an explicit state machine the customer can see. Creating the order takes an
idempotency key, so double-clicks are safe. Inventory reserves stock with one conditional update, `available >= qty`,
so we can't oversell, and the reservation expires after ten minutes. Payment uses the order id as the gateway
idempotency key, and a timeout is treated as unknown until the webhook or a status query confirms it. If payment fails I
release the stock; if payment succeeded but confirmation fails, I retry and finally refund. Events go out through an
outbox, consumers are idempotent, and I alert on orders stuck in a state."

### Q4 [senior] Distributed database trade-offs: CAP, replication, partitioning, and when to favour consistency or availability
tags: cap-theorem, pacelc, replication, partitioning, sharding, quorum, consistency, availability, nagarro, system-design

**Start here: the concepts**
- **CAP:** during a **network partition**, a distributed store must choose between **consistency** (every read sees the latest write, or errors) and **availability** (every request gets an answer, maybe stale).
- **PACELC** adds: *Else* (no partition), choose between **latency** and **consistency**. That is the trade-off you live with every day.
- **Replication** copies data for availability and reads; **partitioning (sharding)** splits data for write scale and size.

**The live scenario (functional requirement)**
*FR: "A retail platform runs in two regions. The product catalogue must stay readable if a region is cut off; account
balances and stock counts must never be wrong."* Same company, two different answers.

**What the interviewer is really checking**
That you apply CAP per **use case**, not per company, and can explain replication modes, quorums and shard keys with
real consequences.

**How I answer it** (120-second answer, point by point)
1. **CAP is about partitions only.** Partitions happen, so the real choice is CP or AP *when* they happen. Without partitions, PACELC's latency-vs-consistency is the everyday trade-off.
2. **Pick per data type:**
   - Catalogue, reviews, recommendations: **AP**. Stale for a few seconds is fine; being down loses sales. Async replication, read from the nearest replica.
   - Balances, stock, payments: **CP**. Better to reject a write than to double-spend. A single leader per key, or a consensus store.
3. **Replication modes:** synchronous (no data loss, higher write latency), asynchronous (fast, may lose the last writes on failover), semi-synchronous (one replica must ack). PostgreSQL streaming replication and Aurora are leader-based; Cassandra/DynamoDB are leaderless with tunable quorums.
4. **Quorums:** with N replicas, reads R and writes W, `R + W > N` gives read-your-latest-write. Cassandra `QUORUM/QUORUM` with N=3 is consistent; `ONE/ONE` is fast and eventually consistent.
5. **Partitioning:** choose a shard key with high cardinality and even traffic (customer id, not country). Hash partitioning spreads load; range partitioning helps range scans but creates hot spots. Plan resharding (consistent hashing, virtual nodes).
6. **Read-your-writes in an AP system:** route a user's reads to the leader for a few seconds after they write, or carry a version token.
7. **Example close:** "for this retailer: catalogue in DynamoDB global tables (AP), orders and stock in Aurora PostgreSQL with one writer region (CP), and events between them via Kafka."

**Trade-offs and what can go wrong**
- Async replication + automatic failover can silently lose the last second of writes. For money, use synchronous or quorum writes.
- Multi-leader across regions gives low write latency but needs conflict resolution (last-write-wins loses data; CRDTs are only for some data types).
- A bad shard key (date, tenant with one giant customer) creates a hot partition that no amount of hardware fixes.

**How I'd monitor it**
Replication lag (seconds and bytes), quorum failures, per-partition throughput (hot-partition detection), failover
events, and read-after-write violations if you sample for them.

**Follow-ups to expect**
- *Is MongoDB CP or AP?* -> With majority write and read concern it behaves CP for a replica set; with weaker concerns, more available but possibly stale.
- *What does eventual consistency mean in practice?* -> If writes stop, all replicas converge; meanwhile reads can be stale, so the UI must tolerate it.
- *How do you reshard without downtime?* -> Double-write or CDC into the new layout, backfill, verify, switch reads, then switch writes.

**60-second answer**
"CAP only applies when a network partition happens: then you choose to stay consistent and reject some requests, or stay
available and serve stale data. The rest of the time the trade-off is latency against consistency, which is PACELC. I
decide per data type, not per system. A product catalogue is AP: asynchronously replicated, read locally, and a few
seconds of staleness is fine. Balances and stock are CP: one leader per key or quorum writes, with R plus W greater than
N, and I'd rather reject a write than oversell. For sharding I pick a high-cardinality, evenly used key and plan for
resharding. And I always watch replication lag, because async failover can lose the last writes."

### Q5 [senior] Design load balancing and failover so a distributed system stays highly available
tags: load-balancing, failover, health-checks, high-availability, multi-az, multi-region, circuit-breaker, kubernetes, nagarro, system-design

**Start here: the concepts**
- A **load balancer** spreads requests across healthy instances. **L4** works on TCP connections; **L7** understands HTTP (paths, headers, cookies).
- **Failover** means traffic moves away from a failed component automatically, to another instance, zone or region.
- **Availability numbers:** 99.9% = about 8.8 hours of downtime a year; 99.99% = about 53 minutes.

**The live scenario (functional requirement)**
*FR: "The customer API needs 99.95% availability. A single pod, node, availability zone or database writer can fail
without customers noticing more than a few seconds of errors."*

**What the interviewer is really checking**
That you can remove single points of failure layer by layer, describe health checks precisely, and know what failover
really costs in time and data.

**How I answer it** (120-second answer, point by point)
1. **Layer by layer, no single point of failure:** DNS (Route 53 with health checks) -> CDN/WAF -> regional L7 load balancer across **3 availability zones** -> Kubernetes Service/Ingress -> pods spread with topology spread constraints -> database with a standby in another zone.
2. **Algorithms:** round robin for uniform requests; **least connections / least outstanding requests** when request cost varies; consistent hashing when you want cache affinity. Avoid sticky sessions: keep services stateless and store sessions in Redis.
3. **Health checks:** readiness (can this pod take traffic now?) removes a pod from rotation; liveness (is it stuck?) restarts it. Readiness checks dependencies lightly; liveness never checks the database, or one database blip restarts everything.
4. **Graceful shutdown:** on SIGTERM, fail readiness, drain in-flight requests (`server.shutdown=graceful`), then exit, so deploys and scale-downs do not drop requests.
5. **Capacity for failure:** with 3 zones, run so that losing one zone leaves enough capacity (N+1). Autoscaling (HPA) handles load, not failure.
6. **Data-tier failover:** Aurora/RDS Multi-AZ promotes a standby in roughly 30-60 s with DNS change; the app needs connection-pool validation and retries with backoff for idempotent calls.
7. **Inside the app:** timeouts on every call, circuit breakers, bulkheads, so a slow dependency does not exhaust threads and take down healthy instances.
8. **Multi-region (only if required):** active-passive with replicated data and DNS failover (RTO minutes, RPO seconds), or active-active with conflict-aware data design. It costs a lot more; justify it with the SLA.

**Trade-offs and what can go wrong**
- Aggressive health checks flap under load and remove healthy pods, causing a cascade. Use thresholds (fail 3 times) and separate readiness from liveness.
- Retries without backoff and jitter multiply traffic during an outage (retry storm).
- DNS failover depends on TTLs and client caching; some clients ignore TTLs for minutes.

**How I'd monitor it**
Healthy host count per target group, 5xx rate at the load balancer vs at the app, p99 latency, failover drills (game
days), and an SLO burn-rate alert for 99.95%.

**Follow-ups to expect**
- *L4 or L7?* -> L7 for HTTP APIs (path routing, TLS termination, header-based canaries); L4 for raw TCP, very high throughput or WebSockets passthrough.
- *How do you test failover?* -> Scheduled chaos tests: kill pods, drain a zone, trigger a database failover in staging, and measure the errors.
- *Active-active or active-passive?* -> Active-passive unless the RTO is seconds and the data model tolerates multi-region writes.

**60-second answer**
"I remove single points of failure layer by layer: DNS with health checks, an L7 load balancer across three zones,
stateless pods spread across zones, and a database with a standby in another zone. I use least-outstanding-requests
balancing and no sticky sessions. Readiness takes a pod out of rotation, liveness restarts it, and liveness never checks
the database. Graceful shutdown drains requests during deploys. I size for N plus one, so losing a zone still leaves
enough capacity. Database failover takes 30 to 60 seconds, so the app retries idempotent calls with backoff, and
timeouts and circuit breakers stop a slow dependency spreading. Multi-region only if the SLA really needs it, and I prove
all of it with failover drills."

### Q6 [senior] Design a notification service for push, email and SMS with retries, rate limiting and personalisation
tags: notification, push, email, sms, retries, rate-limiting, templates, preferences, kafka, dlq, nagarro, system-design

**Start here: the concepts**
- A notification service accepts "notify user X about event Y" and decides **channel, content and timing**, then hands off to providers (FCM/APNs, SES/SendGrid, Twilio).
- Providers are slow and fail sometimes, so everything after the request is **asynchronous** with retries.
- **Rate limiting** protects both users (no spam) and providers (quota limits).

**The live scenario (functional requirement)**
*FR: "Order, payment and marketing services must notify customers. 20 million notifications a day, OTPs within 5
seconds, marketing never at night, and users can opt out per channel."*

**What the interviewer is really checking**
Priorities (an OTP is not a newsletter), idempotency (no duplicate SMS charges), retries with a DLQ, user preferences,
and provider failover.

**How I answer it** (120-second answer, point by point)
1. **API:** `POST /notifications {eventId, userId, type, data}`. `eventId` is the idempotency key.
2. **Pipeline:** API validates and writes to Kafka -> **router** loads user preferences and quiet hours, picks channels, renders the template (per language, with personalisation fields) -> per-channel topics -> **channel workers** call providers.
3. **Priority:** separate topics and worker pools for `critical` (OTP, security), `transactional` (order shipped), `bulk` (marketing). A marketing blast can never delay an OTP.
4. **Idempotency:** a dedupe store keyed by `eventId + channel` (Redis with TTL or a unique DB constraint). Retries never send a second SMS.
5. **Retries:** retryable errors (timeouts, 429, 5xx) go to retry topics with increasing delay (1 min, 5 min, 30 min); permanent errors (invalid number, unsubscribed) go straight to a **DLQ**/failed state. Max attempts, then DLQ with an alert.
6. **Rate limiting:** token bucket per provider (stay under quota), per user (for example max 3 marketing messages a day), and per tenant/service.
7. **Provider failover:** two SMS providers behind a strategy; a circuit breaker on the primary switches traffic to the secondary.
8. **Status tracking:** store each notification's state (queued, sent, delivered, failed) and consume provider webhooks for delivery receipts.
9. **Scheduling:** marketing waits for the user's time zone window; a scheduler releases delayed notifications.

**Trade-offs and what can go wrong**
- At-least-once Kafka delivery + idempotency is simpler than exactly-once and good enough.
- Template rendering at send time gives fresh data; rendering at request time gives an exact audit of what was promised. For legal/transactional text, store the rendered content.
- A retry storm against a failing provider makes it worse: honour `Retry-After`, use the circuit breaker.

**How I'd monitor it**
End-to-end latency per priority (OTP p99 under 5 s), send success rate per provider, DLQ size, retry topic lag,
opt-out/complaint rate, and cost per channel per day.

**Follow-ups to expect**
- *How do you avoid notifying a user ten times for one order?* -> Dedupe by event id, and collapse/aggregate rules ("3 items shipped" instead of three messages).
- *How do you send 10 million marketing emails?* -> Batch through the bulk topic at the provider's rate limit, over hours, with unsubscribe links and suppression lists.
- *Where do preferences live?* -> A preferences service with a cache; read on every route decision.

**60-second answer**
"Callers post an event with an event id, and everything after that is asynchronous through Kafka. A router loads the
user's preferences and quiet hours, picks the channels and renders a localised template, then puts work on per-channel,
per-priority topics, so a marketing blast can never delay an OTP. Channel workers call the providers. The event id plus
channel is the dedupe key, so a retry never sends a second SMS. Retryable errors go through delayed retry topics, and
permanent ones go to a DLQ. Token buckets keep us under provider quotas and stop spamming users, and a circuit breaker
fails over to a second provider. I track every message's status from provider webhooks and alert on OTP latency and
DLQ growth."

### Q7 [senior] Design a near-real-time clickstream (or IoT) data pipeline for analytics
tags: data-pipeline, clickstream, iot, kafka, stream-processing, flink, lakehouse, s3, schema-registry, late-events, nagarro, system-design

**Start here: the concepts**
- **Ingestion** collects events; **stream processing** cleans and aggregates them continuously; **storage** keeps raw data (data lake) and query-ready data (warehouse/OLAP).
- **Event time** (when it happened) differs from **processing time** (when we saw it); mobile and IoT events arrive late.
- A **schema registry** enforces event formats so a producer change does not break every consumer.

**The live scenario (functional requirement)**
*FR: "Capture page views and clicks from web and mobile apps (50,000 events/s at peak). Product managers want dashboards
updated within one minute, and data scientists want the full raw history."*

**What the interviewer is really checking**
A lambda/kappa-style split between real-time and historical, partitioning and back-pressure in Kafka, late-event
handling, schema evolution and data quality.

**How I answer it** (120-second answer, point by point)
1. **Collect:** SDKs batch events and send to an **ingestion API** (stateless, autoscaled) that validates basic shape, adds server time, and produces to Kafka. Mobile buffers offline.
2. **Kafka:** topic `clickstream.raw`, keyed by `sessionId` (keeps a session ordered), 50k events/s x 1 KB = 50 MB/s: about 50-100 partitions, replication factor 3, 7-day retention.
3. **Schema:** Avro/Protobuf with a schema registry and backward-compatible evolution rules.
4. **Raw zone:** a sink connector writes Kafka to **S3** in Parquet, partitioned by date/hour. This is the replayable source of truth (data lake / Iceberg tables).
5. **Real-time path:** **Flink** (or Kafka Streams) does dedupe by event id, bot filtering, enrichment (geo, device), sessionisation, and 1-minute tumbling-window aggregates using **event time with watermarks** (allow 5 minutes lateness). Results go to an OLAP store (ClickHouse/Druid/Pinot) for dashboards.
6. **Batch path:** daily Spark/dbt jobs on the lake recompute exact metrics and correct anything the stream approximated; the warehouse serves analysts.
7. **Data quality:** invalid events go to a quarantine topic with a reason; row counts reconcile raw vs aggregated.
8. **Privacy:** hash or drop PII at ingestion, honour consent flags, retention policies for GDPR deletion.

**Trade-offs and what can go wrong**
- Kappa (stream only, replay from the lake) is simpler to run; Lambda (stream + batch) gives correct late-data numbers but two code paths. I start with the stream and add batch correction for finance-grade metrics.
- Watermarks too strict drop late events; too lenient delay dashboards. Pick from the measured lateness distribution.
- A hot key (one huge customer or bot) skews one partition; add salting or filter bots early.

**How I'd monitor it**
Ingestion rate vs expected, Kafka consumer lag per job, end-to-end freshness (event time to dashboard), dropped-late
event count, quarantine rate, and S3 sink file counts (small-file problem).

**Numbers I quote**
- 50k events/s x 1 KB = 50 MB/s = about 4.3 TB/day raw (much less as compressed Parquet, often 5-10x).

**Follow-ups to expect**
- *Exactly-once?* -> Flink checkpoints with transactional sinks, or idempotent upserts keyed by window + dimension.
- *How do you replay after a bug?* -> Reprocess from S3/Kafka retention into a new output table, then swap.
- *Why not write straight to the database?* -> 50k writes/s of tiny rows overloads OLTP; Kafka absorbs bursts and decouples consumers.

**60-second answer**
"SDKs batch events to a stateless ingestion API that writes to Kafka, keyed by session, with Avro schemas in a registry.
At 50,000 events a second that's about 50 MB a second, so I'd use around 64 partitions with replication factor three. A
sink connector lands raw events in S3 as Parquet, which is our replayable source of truth. Flink dedupes, filters bots,
enriches, and builds one-minute aggregates on event time, with watermarks that allow a few minutes of lateness. It writes
them to ClickHouse or Druid for dashboards. A daily batch job on the lake corrects late data for exact numbers. Bad
events go to a quarantine topic, and I monitor lag and end-to-end freshness."

### Q8 [senior] Security in application design: authentication, authorisation, encryption and secure APIs
tags: security, oauth2, oidc, jwt, authorization, rbac, abac, encryption, tls, secrets, owasp, spring-security, nagarro, system-design

**Start here: the concepts**
- **Authentication** = who are you (login, OIDC). **Authorisation** = what are you allowed to do (roles, scopes, ownership).
- **OAuth 2.0** issues access tokens; **OpenID Connect** adds identity on top. A **JWT** is a signed token the API can verify without calling the auth server.
- **Encryption in transit** (TLS) and **at rest** (KMS-managed keys) are baseline; **secrets** never live in code or images.

**The live scenario (functional requirement)**
*FR: "A customer portal (web + mobile) and partner integrations call our microservices. Customers may only see their own
orders, partners only their own tenant's data, and the platform must pass a security review."*

**What the interviewer is really checking**
Defence in depth, a correct OAuth flow per client type, object-level authorisation (the most common real breach), and
secret/key handling, explained practically with Spring Security.

**How I answer it** (120-second answer, point by point)
1. **Identity provider:** Keycloak/Okta/Entra ID/Cognito. Web and mobile use **Authorization Code + PKCE**; partners use **client credentials** (machine to machine). No passwords stored in our services.
2. **Edge:** API gateway terminates TLS, validates the JWT (signature via JWKS, issuer, audience, expiry), applies rate limits and a WAF. Internal traffic uses mTLS (service mesh) or short-lived service tokens.
3. **Services:** Spring Security as an **OAuth2 resource server** re-validates the token (zero trust: never trust the network alone). Coarse rules by scope/role: `hasAuthority('SCOPE_orders.read')`.
4. **Object-level authorisation (BOLA, OWASP API #1):** every query filters by the caller: `findByIdAndCustomerId(id, principal.customerId)`. Changing `/orders/123` to `/orders/124` must return 404, not someone else's order.
5. **Input and output:** validate DTOs (`@Valid`), parameterised queries (no SQL injection), never return entities directly (no mass assignment or data leaks), generic error messages (Problem Details without stack traces).
6. **Encryption:** TLS 1.2+ everywhere; databases and S3 encrypted with KMS keys; sensitive fields (PAN, national ids) tokenised or field-level encrypted; passwords, if ever stored, with bcrypt/argon2.
7. **Secrets:** Vault or AWS Secrets Manager, injected at runtime, rotated; IAM roles instead of access keys.
8. **Supply chain and process:** dependency scanning (OWASP Dependency-Check/Snyk), SAST in CI, container image scanning, threat modelling for new features, audit logs of who accessed what.

**Trade-offs and what can go wrong**
- JWTs are fast to verify but cannot be revoked instantly: keep them short-lived (5-15 min) with refresh tokens, or use introspection for high-risk actions.
- Gateway-only authorisation leaves services open to anyone inside the network; validate in both places.
- Logging tokens or PII in plain text turns your log platform into a breach.

**How I'd monitor it**
Auth failure rate (401/403 spikes = credential stuffing or a broken client), WAF blocks, unusual access patterns per
user (many object ids enumerated), secret rotation age, and dependency CVE dashboards.

**Follow-ups to expect**
- *Where do you store tokens in a browser?* -> Prefer a backend-for-frontend with HttpOnly, Secure, SameSite cookies; avoid long-lived tokens in localStorage.
- *Roles or attributes?* -> RBAC for coarse access, ABAC/ownership checks for data-level decisions.
- *How do services call each other securely?* -> mTLS via the mesh plus client-credential tokens with narrow scopes.

**60-second answer**
"I separate authentication from authorisation and use defence in depth. An identity provider issues tokens:
authorization code with PKCE for web and mobile, client credentials for partners. The gateway terminates TLS, validates
JWTs and rate-limits, and each Spring Boot service is still an OAuth2 resource server that re-checks the token and
scopes. The most common real breach is object-level, so every query filters by the caller's customer or tenant id. I
validate inputs, return DTOs not entities, and use parameterised queries. Data is encrypted in transit and at rest with
KMS keys. Secrets come from Vault or Secrets Manager, never code, and CI scans dependencies and images."
