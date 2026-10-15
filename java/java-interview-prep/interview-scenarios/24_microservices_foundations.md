---
id: foundations-microservices
title: Microservices architecture: from the basics (drafted)
stack: java
skill: microservices
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] What is a microservice and what are the benefits and costs?
tags: microservices, bounded-context, data-ownership, distributed-systems, resilience, basics

**Start here: the concepts**
- **Monolith:** one application, built and deployed as a single unit. All features (catalog, checkout, payments) live in one codebase and one running process. Microservices are usually compared against it.
- **Microservice:** a small application that does one job for the business (for example "payments") and runs on its own. "Small" does not mean few lines of code. It means a focused responsibility that one team can understand and own.
- **Business capability / bounded context:** a part of the business with its own language and rules, such as "orders" or "inventory". Services are cut along these lines, not along technical layers.
- **Independently deployable:** you can release one service without rebuilding or redeploying the others. This is the core idea. If you must deploy five services together, you have a "distributed monolith".
- **Data ownership:** each service has its own database or schema, and only that service reads or writes it. Others must ask through its API. This stops teams from breaking each other through shared tables.
- **Fault isolation:** a failure in one service should not take down the others. It does not happen automatically. You must design for it with timeouts and fallbacks.
- **Network failure / partial failure:** calls between services travel over a network, so they can be slow, time out, or fail while the rest of the system is fine.
- **Eventual consistency:** data in different services may be briefly out of step and become correct a little later. This happens because one database transaction can no longer cover everything.
- **Operational overhead:** with N services you deploy, monitor, secure, and upgrade N things instead of one.

**The live scenario**
An online shop runs as a monolith with 8 teams. It releases every two weeks because every change needs full regression testing. During a sale, checkout traffic is about 50x normal, but the team must scale the whole app to 20 instances. A memory leak in the recommendations module crashes the process and checkout is down for 25 minutes. The company extracts checkout, payments, and catalog into separate services. Checkout now scales alone, teams deploy daily, and a recommendations crash no longer stops purchases. But a new problem appears: an order shows "paid" while inventory was never reserved, and the team needs a day to trace it across four services.

**What the interviewer is really checking**
Whether you see microservices as a trade-off rather than "modern and better". A fresher should define the idea correctly (business capability, own data, independent deploys) and name the costs honestly.

**How I answer it**
1. **Define it by business capability and independence, not size.** The service does one business job and can be deployed alone. This matters because the benefits all come from independence.
2. **Say it owns its data.** No shared database. Otherwise a schema change in one service breaks others, and independence is lost.
3. **List the benefits with the reason for each.**
   - Independent scaling: scale only checkout during a sale.
   - Independent deploys: small changes ship without a full-system release.
   - Team autonomy: a team owns a service end to end.
   - Fault isolation: one failure can stay contained, if timeouts and fallbacks exist.
   - Technology choice: each service can use the language or database that fits it.
4. **List the costs with the reason for each.**
   - Network failures: calls are slower and less reliable than in-process method calls.
   - Distributed data consistency: there is no single transaction across services, so you need patterns like sagas and eventual consistency.
   - Testing and debugging: one request crosses many services, so you need integration tests and tracing.
   - Operational overhead: you need automated deployment, monitoring, and security for every service.
5. **Close with judgement.** Microservices pay off when the organization and scale are big enough. For a small team or an unclear domain, a well-structured monolith is often better.

**Trade-offs and what can go wrong**
- Splitting too finely creates chatty services, high latency, and a distributed monolith.
- A shared database hides coupling and removes the main benefit.
- Calls without timeouts or retry limits let one slow service drag down its callers (a cascading failure).
- Teams adopt microservices before they have automated deployment and monitoring, so the operational cost overwhelms them.
- Never claim microservices are "always better". The stored claim of "fault isolation" is only true when resilience is designed in.

**How I'd monitor it**
- Per-call latency (p95/p99), error rate, and timeouts between services.
- Circuit-breaker state and retry counts.
- Distributed traces, with a correlation id passed in every request and log line. In Splunk: `index=app correlationId="abc-123" | sort _time` shows one request's path across services.
- Deploy frequency and failure rate, to confirm the independence benefit is real.
- Alerts on error-rate spikes per service.

**Follow-ups to expect**
- *How do you keep data consistent across services?* -> Avoid distributed transactions (2PC). Use a saga (a chain of local transactions with compensating actions), the transactional outbox to publish events reliably, and idempotent consumers to handle duplicates.
- *When would you not use microservices?* -> For a small team, an early product, or an unclear domain. A modular monolith is simpler and can be split later.
- *Sync or async between services?* -> Use sync (REST) when the caller needs an immediate answer. Use async (messaging such as Kafka) when work can happen later or you want looser coupling.

**60-second answer**
A microservice is a small, independently deployable service that owns one business capability and its own data. Because it deploys and scales on its own, teams move faster, we scale only the busy parts, and a failure can stay contained if we add timeouts and fallbacks. We can also pick the technology that suits each service. The costs are real. Calls cross a network and can fail. Data is spread across services, so we accept eventual consistency and use patterns like sagas. Testing and debugging get harder, so we need tracing with correlation ids. And we must deploy, monitor, and secure many services instead of one. So I choose microservices when team size and scale justify that cost, and otherwise start with a well-structured monolith.

### Q2 [fresher] How do you decide service boundaries?
tags: microservices, domain-driven-design, bounded-context, data-ownership, coupling-cohesion, basics

**Start here: the concepts**
- **Microservice:** a small program that does one business job, runs on its own, and is deployed on its own. It exists so teams can change and release their part without waiting for everyone else.
- **Service boundary:** the line that decides what is inside one service and what belongs to another. Drawing it wrongly is the most expensive microservices mistake, because moving it later means rewriting code and migrating data.
- **Domain-Driven Design (DDD):** a way of designing software by first understanding the business (the "domain") and shaping the code around how the business talks and works.
- **Bounded context:** an area where each word has one clear meaning. "Customer" in Billing (a payer with an address) differs from "Customer" in Support (a person with tickets). Each context gets its own model, and often its own service.
- **Business capability:** something the business does, such as taking orders, charging payments or tracking stock. Boundaries follow these, not code layers.
- **Cohesion:** how closely related the things inside a service are. High cohesion means everything inside serves the same purpose.
- **Coupling:** how much one service depends on another. Low coupling means a change in one rarely forces a change in the other.
- **Data ownership:** only the owning service reads and writes its tables. Others must ask it through its API or events.

**The live scenario**
A team of 12 builds a shop. They split by technical layer: a "Web service", a "Logic service" and a "DB service" that every feature calls. Adding a "gift message" field to orders means changing all three, coordinating three releases, and it takes 2 weeks. When the DB service is slow, all 30 endpoints slow down, and one bad deploy takes the whole shop offline. They redraw the boundaries as **Orders**, **Payments** and **Inventory**, each with its own team and database. The same change now touches only Orders and ships in a day.

**What the interviewer is really checking**
Whether you split by business meaning rather than technical layers, and whether you understand that each service owns its data and that every split has a cost.

**How I answer it**
1. **Learn the business first.** Talk to the people who run it and list what it does (orders, payments, stock). Reason: boundaries that match the business change when the business changes, not randomly.
2. **Draw bounded contexts around those capabilities.** Reason: inside a context the words and rules are consistent, so the model stays simple.
3. **Aim for high cohesion inside, low coupling between.** Reason: if a service must call five others to finish one task, the boundary is probably wrong.
4. **Test each boundary with "does it change for one reason, and can one team own it?"** Reason: if one business change forces edits in three services, or two teams fight over one service, the line is misplaced.
5. **Give each service its own data.** Reason: a shared database is hidden coupling, because changing a table can silently break another service.
6. **Never split by technical layer.** A "DB service" or "validation service" is a smell, because every feature crosses it and it becomes a bottleneck and a single point of failure.
7. **When unsure, start bigger.** Keep a well-organised single application with clear modules and split later. Reason: merging wrongly split services is harder than splitting a clean module.

**Trade-offs and what can go wrong**
- Too small ("nano-services") means many network calls, slow and fragile chains, and heavy operations work.
- Too big means you get a mini-monolith where teams block each other.
- Splitting data means no single database transaction across services, so you accept eventual consistency and need patterns such as sagas.
- Debugging now spans services, so you need correlation ids and tracing.
- Boundaries guessed before understanding the domain are usually wrong.

**How I'd monitor it**
- **Deployment coupling:** how often service A cannot be released without B. If it is frequent, the boundary is wrong.
- **Call depth:** use distributed traces (for example OpenTelemetry) to look at the chain length per request. Illustratively, more than 3-4 synchronous hops is a warning.
- **Logs:** in Splunk, search by correlation id to see which services one request touches, and group by service pair to find "chatty" pairs.
- **Change failure and lead time per team,** plus a count of cross-team pull requests.

**Follow-ups to expect**
- *Why not one service per database table?* -> That gives anemic, chatty services with no business meaning. Boundaries follow capabilities, not tables.
- *What if two services need the same data?* -> One owns it and exposes it through an API or events. The other keeps its own copy of only what it needs.
- *Should a new project start with microservices?* -> Often no. Start as a modular monolith and extract services once the boundaries are proven.

**60-second answer**
I decide service boundaries from the business, not from technology. Using Domain-Driven Design, I find the bounded contexts, areas like Orders, Payments and Inventory where each term has one clear meaning. Each service should have high cohesion inside and low coupling to others. A good test is that it changes for one reason and one team can own it. Each service owns its own data, and I never split by technical layer, like a "DB service", because every feature then crosses it. If I am unsure about the boundaries, I start with a modular monolith, because splitting too early gets expensive.

### Q3 [mid] Synchronous vs asynchronous communication?
tags: microservices, synchronous, asynchronous, rest, grpc, kafka, basics

**Start here: the concepts**
- **Synchronous communication:** the caller sends a request and waits, doing nothing else, until the reply arrives. A phone call is a good analogy. REST (HTTP with JSON) and gRPC (a faster binary protocol over HTTP/2) work this way.
- **Asynchronous communication:** the sender puts a message on a broker and moves on without waiting. Other services read it when they are ready. This is like sending a letter. Kafka and RabbitMQ are brokers, meaning middlemen that store messages until they are consumed.
- **Command:** a request to do something specific, such as "charge this card". The sender needs to know the outcome.
- **Event:** a statement that something already happened, such as "OrderPlaced". The sender does not care who reacts, and many services can react.
- **Availability coupling:** if service A must call B to finish, A works only when B works. Availabilities multiply, so four services at 99.9% each give about 99.6% for the chain.
- **Fan-out:** one message delivered to many independent consumers.
- **Eventual consistency:** after a change, other services catch up a little later instead of instantly.
- **Spike absorption (buffering):** the broker holds a burst of messages so consumers can work through them at their own pace.

**The live scenario**
A checkout service handles 200 orders per second. For each order it calls payment, inventory, email, and loyalty points, one after another over REST. Normally p99 latency (the slowest 1% of requests) is 400 ms. During a sale, the email service slows down. Checkout threads sit waiting on it, p99 jumps to 6 s, the thread pool fills, and customers can't buy even though payment is healthy. The team keeps payment and inventory synchronous because the customer needs an answer. They publish an `OrderPlaced` event for email, loyalty, and analytics. Checkout latency returns to about 450 ms, and a slow email service now only builds a backlog.

**What the interviewer is really checking**
Whether you choose the style from the business need (does the caller need the answer now?) instead of from habit, and whether you understand the costs of each, especially eventual consistency and debugging.

**How I answer it**
1. **Define both styles briefly.** Sync means call and wait. Async means publish and move on. This shows you know the basic difference.
2. **Name what sync gives and costs.** It is simple, easy to debug, and returns an immediate answer. But it couples availability and latency: the caller is only as fast and as reliable as its slowest dependency.
3. **Name what async gives and costs.** It decouples services in time, absorbs spikes, and lets many consumers react to one event. The cost is eventual consistency and flows that are harder to trace.
4. **Give the rule of thumb.** Commands that need an immediate answer use sync. Facts others react to use events. Payment authorization is sync because the user must know the result. "Order placed, now send an email" is an event because the order doesn't depend on it.
5. **Add the nuance.** The rule is a guideline, not a law. A command can be sent asynchronously through a queue when the user can wait, for example "generate my report". Async also doesn't remove all coupling, because services still share the event's schema, so it needs versioning.
6. **Mention the safety nets.** Sync calls need timeouts, retries with backoff, and circuit breakers. Async consumers must be idempotent, meaning safe to process the same message twice, because brokers can redeliver.

**Trade-offs and what can go wrong**
- Long sync chains make failures cascade, and retries can multiply load on an already struggling service.
- Async makes the user experience harder: the UI must handle "we're processing your order" instead of an instant final state.
- Lost or duplicated messages: publishing to the broker and writing to the database can fail separately, and the transactional outbox pattern addresses this. Duplicates require idempotent consumers.
- Using events for everything leads to hidden flows that no one can follow end to end.
- Debugging spans several services and a broker, so correlation IDs are essential.

**How I'd monitor it**
- **Sync:** p99 latency and error rate per downstream call, thread pool usage, and circuit breaker open/close state.
- **Async:** Kafka consumer lag (how far behind consumers are), dead-letter queue size, and message age.
- **Both:** pass a correlation ID in HTTP headers and message headers, use distributed tracing, and in Splunk search by that ID to follow one order across services.
- Alert on rising lag and on latency growth in a single dependency.

**Follow-ups to expect**
- *Can async support a request/response style?* -> Yes. The caller sends a message with a reply address and correlation ID, and the response arrives on another queue. It is more complex than REST, so use it only when you need the buffering.
- *How do you avoid losing an event after a database commit?* -> Use the transactional outbox: write the event to an outbox table in the same transaction, then a relay publishes it. Consumers stay idempotent because delivery is at-least-once.
- *How do you protect a sync call to a flaky service?* -> Set a timeout, retry with backoff only for idempotent calls, add a circuit breaker, and provide a fallback where possible.

**60-second answer**
Synchronous means the caller sends a request and waits, as with REST or gRPC. It's simple and gives an immediate answer, but it ties my availability and latency to the services I call. Asynchronous means I publish a message to something like Kafka or RabbitMQ and move on. That decouples services, absorbs traffic spikes, and lets many consumers react, but the system becomes eventually consistent and harder to trace. My rule is that commands needing an immediate answer, like payment authorization, are sync, and facts others react to, like "order placed", are events. I protect sync calls with timeouts and circuit breakers, and I make consumers idempotent. I monitor latency, consumer lag, and use correlation IDs to trace requests across services.

### Q4 [mid] Why "database per service" and how do you handle joins?
tags: microservices, database-per-service, data-ownership, api-composition, cqrs, read-model, event-driven, basics

**Start here: the concepts**
- **Database per service:** each microservice is the only owner of its tables. Other services cannot read or write them directly and must ask the owner through its API or its published events. It can be a separate schema or a separate server; what matters is that no one else touches it.
- **Schema coupling:** if two services read the same tables, a column rename or type change in one can break the other. Then you cannot deploy them independently, which was the main reason to split them.
- **Join:** a SQL operation that combines rows from two tables in one query. It only works when both tables sit in the same database, so with separate databases you must combine the data some other way.
- **API composition:** one component (an aggregator, or a BFF, "backend for frontend", which is an API layer built for one client such as the mobile app) calls several services and merges their answers in memory.
- **Event:** a message saying "something happened", such as `CustomerRenamed`, usually sent through a broker like Kafka.
- **Read model:** a separate, query-friendly copy of data, built by listening to events from several services. This is the query side of **CQRS** (Command Query Responsibility Segregation), which uses one model for writes and another for reads.
- **Eventual consistency:** copies of data may be slightly out of date, but they catch up after a short delay.

**The live scenario**
An e-commerce company has Orders, Customers and Catalog services sharing one database. At 2 a.m. the Customers team renames a column. The Orders service starts failing at about 500 checkouts per second, and the incident lasts 40 minutes. After the post-mortem, each service gets its own database. The "My Orders" screen still needs the order, the customer name and the product title, and the old three-table join no longer works. The team has to decide how to build that screen.

**What the interviewer is really checking**
Whether you understand that data ownership is what gives independence, and whether you know the practical replacements for joins along with their cost: eventual consistency.

**How I answer it**
1. **Give each service sole ownership of its data.** Others get access only through an API or events. This way a schema change stays private to the owner and each team can deploy on its own. A shared database is a hidden contract that breaks without warning.
2. **State that cross-service joins are gone, and pick a replacement per use case.**
3. **Use API composition for simple, low-volume queries.** A BFF calls Orders, Customers and Catalog (in parallel where possible) and merges the results. It is easy to build and always fresh. The weakness is that latency is roughly that of the slowest call, and availability drops because any one failing service affects the page. So add timeouts and fallbacks.
4. **Use a CQRS read model for heavy or high-traffic queries.** A "My Orders" service consumes `OrderPlaced`, `CustomerRenamed` and `ProductUpdated` events and stores a denormalised document that already holds the customer name and product title. Reads are one fast lookup with no runtime calls to other services. The cost is that the data is eventually consistent.
5. **Replicate small reference data through events.** For example, Orders keeps a local copy of just the customer fields it needs. It reads them locally, but the owner remains the source of truth.
6. **Publish events reliably.** Write the data change and the event in the same local transaction (transactional outbox), and make consumers idempotent, meaning that processing the same event twice does no harm. Otherwise copies silently drift.

**Trade-offs and what can go wrong**
- Data is duplicated and stale for a short time. Product and business must accept this (a renamed customer shows the old name for a few seconds).
- Aggregators can create call chains where one slow service slows the whole page.
- If a service reads another service's database "just this once", you have rebuilt the shared database.
- Events can be lost, duplicated or arrive out of order, so you need the outbox, idempotency and versioning.
- You can no longer enforce foreign keys or run ACID transactions across services; use sagas for multi-service workflows.
- Debugging is harder because one request touches many services.

**How I'd monitor it**
- Consumer lag on the Kafka topics that feed read models, and the age of the newest event applied (projection freshness).
- Aggregator p95/p99 latency, plus error and timeout rates per downstream call.
- Circuit breaker state and fallback counts.
- Dead-letter queue size.
- A correlation id on every request and event, so one Splunk search on that id shows the full path across services.
- A periodic reconciliation job that compares read-model counts with the source services.

**Follow-ups to expect**
- *What if the read model is wrong or lost?* -> Rebuild it by replaying events from Kafka (if retention allows) or from a snapshot of the source service. This is a big advantage of event-built read models.
- *Can I just let services share a database but use different schemas?* -> It is acceptable as a short-term step. It only works if access is strictly separated, and it still ties deployment and scaling together, so it is not true independence.
- *How do you keep a multi-service write consistent?* -> Use a saga: a chain of local transactions with compensating actions, instead of a distributed transaction (2PC).

**60-second answer**
Each microservice owns its data, because a shared database couples services at the schema level. A change by one team can break another, and we lose independent deployment. Others get the data only through the owner's API or events. Since cross-service joins are no longer possible, I choose per use case. For simple queries I use API composition: a BFF calls the services and merges the results. For heavy reads I build a CQRS read model from events, so one lookup returns everything. For small reference data I replicate it locally through events. The price is eventual consistency and more moving parts, so I use the outbox and idempotent consumers, and I monitor consumer lag and trace requests with correlation ids.

### Q5 [mid] What is the Transactional Outbox pattern and why?
tags: microservices, transactional-outbox, kafka, cdc, dual-write, idempotency, basics

**Start here: the concepts**
- **Database transaction:** a group of writes that either all succeed or all fail together. It only covers one database.
- **Dual write:** changing two separate systems (e.g. the DB and Kafka) in one piece of code. There is no shared transaction across them, so one write can succeed while the other fails.
- **Event:** a small message saying "something happened", e.g. `OrderCreated`. Other services react to it.
- **Outbox table:** an ordinary table in the service's own database. Each row is an event waiting to be published.
- **Relay:** a separate process that reads new outbox rows and publishes them to Kafka. It is either a **poller** (queries the table every few hundred ms) or **CDC** (change data capture), where a tool such as Debezium reads the database's transaction log and streams new rows out without querying the table.
- **At-least-once delivery:** an event is never lost, but may be delivered more than once.
- **Idempotent consumer:** a consumer that gives the same result if it sees the same event twice. It usually stores processed event ids and skips repeats.

**The live scenario**
An order service handles about 2,000 orders/minute. The code does `save(order)` and then `kafkaTemplate.send(OrderCreated)`. During a Kafka broker restart, about 40 orders were saved but their events were never sent. Payment and shipping never heard about them, and customers waited with no update. Reversing the order (publish first, then save) is no better: if the DB commit fails, downstream services act on an order that doesn't exist. The team adopted an outbox, and the lost and phantom events stopped.

**What the interviewer is really checking**
Whether you understand why the dual-write problem exists, how the outbox solves it, and that you know the guarantee is at-least-once, so consumers must handle duplicates.

**How I answer it**
1. **Name the problem.** The DB and Kafka cannot share one transaction. Distributed transactions (2PC/XA) are slow, poorly supported by Kafka and fragile, so I avoid them. Any code that writes to both can leave them inconsistent.
2. **Write the event inside the same DB transaction as the business change.** The order row and the outbox row commit together or not at all. The database now guarantees that if the order exists, its event exists too.
3. **Publish from the outbox with a relay.** A poller is simple but adds latency and DB load. CDC such as Debezium is faster and puts no polling queries on the DB, but you must run and operate it. The relay marks or deletes rows only after Kafka confirms the send.
4. **Accept at-least-once.** If the relay sends an event and crashes before recording it, it will send the event again after restart. That is a duplicate, never a loss.
5. **Make consumers idempotent.** Each event carries a unique id, and the consumer records processed ids (ideally in the same transaction as its own change) and skips repeats.
6. **Preserve ordering where needed.** Use the aggregate id (e.g. `orderId`) as the Kafka message key so all events for one order go to the same partition, in order.

```sql
BEGIN; INSERT INTO orders ...; INSERT INTO outbox(id, aggregate_id, type, payload) ...; COMMIT;
```

**Trade-offs and what can go wrong**
- Extra moving part: a table, a relay, and cleanup. The outbox grows forever unless old rows are deleted or archived.
- Added latency (poll interval or CDC lag), so consumers see the data eventually, not instantly.
- Duplicates are normal. If consumers are not idempotent, you can double-charge.
- A poller running on several instances can publish the same row twice or break ordering unless rows are locked or claimed safely.
- It only protects the "DB to Kafka" step. It does not by itself undo a failed multi-service business flow. That needs a saga.
- Don't publish a payload that is out of sync with the DB. Build it from the data inside the transaction.

**How I'd monitor it**
- Count of unpublished outbox rows and age of the oldest one. Alert if the age exceeds, say, a minute.
- Relay error and retry rates; Debezium connector status and lag.
- Kafka producer error rate, and consumer lag on downstream topics.
- Duplicate-skip counter in consumers, to see how often redelivery happens.
- Splunk search by event id or correlation id to follow one event from the order service through the relay to the consumers.

**Follow-ups to expect**
- *Why not just use Kafka transactions?* -> Kafka transactions cover only Kafka reads and writes. They cannot include your database commit, so the dual-write gap remains.
- *Poller or CDC?* -> Poller is simpler for low volume. CDC gives lower latency and no polling load but needs more operational effort.
- *Does the outbox give exactly-once?* -> No. It gives at-least-once publishing. Exactly-once effect comes from idempotent consumers.

**60-second answer**
The problem is that a service can't write to its database and to Kafka in one atomic step. If one succeeds and the other fails, the data and the events disagree. With the transactional outbox, I save the business change and an event row in an outbox table in the same database transaction, so both commit or neither does. A separate relay, either a poller or CDC like Debezium, reads the outbox and publishes to Kafka, marking rows done only after Kafka confirms. This guarantees events are never lost, but they can be delivered twice, so consumers must be idempotent and skip event ids they have already processed. The costs are an extra table and relay, some delay, and cleanup, and I would monitor the oldest unpublished row and consumer lag.

### Q6 [mid] How do you handle distributed transactions without 2PC?
tags: distributed-transactions, saga, transactional-outbox, idempotency, eventual-consistency, microservices, basics

**Start here: the concepts**
- **Distributed transaction:** one business action that must change data in several services, each with its own database, so that either all changes happen or none do. A single database does this with a normal transaction. Separate databases cannot.
- **2PC (two-phase commit, XA):** a coordinator asks every database "can you commit?" (phase 1), then tells all of them "commit" (phase 2). Each participant holds locks while it waits. If the coordinator or one participant stalls, everyone stays blocked, which hurts availability. Most managed cloud messaging services (for example SQS or SNS) do not support XA.
- **Aggregate:** a group of data that always changes together, such as an order and its lines. If it lives in one service and one database, a normal local transaction covers it.
- **Saga:** a chain of local transactions, one per service. If a step fails, earlier steps are undone by compensating actions (for example "refund payment"). *Choreography* means services react to each other's events. *Orchestration* means one coordinator tells each service what to do next.
- **Transactional outbox:** a service writes its data change and an "event to publish" row in the same local transaction. A separate process then publishes the row to the broker. This avoids saving data but losing the event, or the reverse.
- **Idempotent operation:** doing it twice has the same effect as doing it once. This matters because messages are usually delivered at least once, so duplicates will arrive.
- **Eventual consistency:** data across services may disagree briefly, but converges.
- **Reconciliation job:** a scheduled check that compares services and repairs differences.

**The live scenario**
An e-commerce platform handles about 2,000 orders a minute. Order, Payment and Inventory are separate services. The first design used XA across all three databases. When Inventory's database slowed down, its locks were held for seconds. Order and Payment threads piled up behind it, and checkout latency went from 300 ms to 12 s. About 5% of checkouts failed for 20 minutes. The team moved to a saga with an outbox. Inventory trouble now only delays the reservation step, and the other services keep working.

**What the interviewer is really checking**
Whether you know *why* 2PC is avoided and can name the practical replacements (saga, outbox, idempotency). Also whether you admit the cost: eventual consistency and extra failure handling.

**How I answer it**
1. **Avoid the problem first.** Draw service boundaries so that data that must change together lives in one service's aggregate. A local transaction is simple and safe, and it is the best "distributed transaction" because there isn't one.
2. **If a business process truly spans services, use a saga.** Each service commits locally, then triggers the next step. I choose choreography for 2-3 simple steps and orchestration when the flow is long or has many branches, because one place then shows the flow.
3. **Define a compensation for every step.** There is no global rollback, so "payment taken" needs "refund". Compensations must be business-level actions, not database rollbacks.
4. **Use the outbox to publish events reliably.** Writing to the database and sending to the broker are two systems, and either can fail between the two. Writing both into one local transaction closes that gap.
5. **Make every consumer idempotent.** Store a processed message ID, or use natural keys and upserts, so a redelivered "charge order 42" does not charge twice.
6. **Accept eventual consistency and design the UI for it.** Show "order pending" rather than pretending everything is instant.
7. **Add reconciliation jobs.** Despite all this, drift happens (bugs, lost messages, manual fixes). A nightly job finds, for example, paid orders with no shipment and repairs or alerts.

**Trade-offs and what can go wrong**
- More code and more states (pending, failed, compensated) to design and test.
- Users can briefly see intermediate states. Some actions cannot be undone, such as an email already sent, so order the steps so the irreversible one comes last.
- Outbox publishing gives at-least-once delivery, so duplicates are normal.
- Choreography can turn into a tangle of events nobody can follow. Orchestration adds a component that must itself be reliable.
- Debugging spans services, so correlation IDs and tracing are essential.

**How I'd monitor it**
- Count sagas by state and age, and alert on ones stuck in "pending" beyond a threshold.
- Track outbox backlog (unpublished rows and age of the oldest) and consumer lag on the broker.
- Track compensation rate and dead-letter queue size.
- Search logs (for example in Splunk) by correlation ID to follow one order across services.
- Alert on reconciliation job findings; a rising count signals a bug.

**Follow-ups to expect**
- *Choreography vs orchestration?* -> Choreography is decentralised events, which is fine for short flows. Orchestration uses a central coordinator, which gives visibility and control for complex flows.
- *Why is the outbox needed?* -> Without it, a crash between "save to DB" and "publish event" loses the event or publishes a phantom one.
- *What if a compensation fails?* -> Retry it (it is idempotent), then send it to a dead-letter queue and alert for manual or reconciliation repair.

**60-second answer**
I first try to avoid distributed transactions by keeping data that must change together inside one service, where a normal local transaction works. 2PC (XA) holds locks across systems, so one slow participant blocks everyone, and most cloud messaging does not support it. For cross-service flows I use a saga: each service commits locally and undoes earlier steps with compensating actions if something fails. I publish events with a transactional outbox so the data change and the event cannot get out of step. Consumers are idempotent because duplicates will happen. I accept eventual consistency, and I run reconciliation jobs to detect and repair drift. I monitor stuck sagas, outbox backlog and consumer lag.

### Q7 [mid] Which resilience patterns do you apply on every remote call?
tags: microservices, resilience, timeout, retry, circuit-breaker, bulkhead, basics

**Start here: the concepts**
- **Remote call:** one service calling another over the network. It can be slow, fail, or hang, and the caller cannot tell which until it waits.
- **Timeout:** a maximum wait. Without one, a hung call holds a thread forever.
- **Retry with backoff and jitter:** try again after a failure. Backoff means waiting longer each time. Jitter adds randomness so thousands of clients don't retry at the same instant.
- **Idempotent:** doing it twice has the same effect as doing it once (a GET, or a POST protected by an idempotency key). Only these are safe to retry.
- **Circuit breaker:** like an electrical fuse. After too many failures it "opens" and fails calls instantly for a while, giving the sick service room to recover.
- **Bulkhead:** a separate, limited pool of threads or permits per dependency, like ship compartments. One slow dependency can't use up all your threads.
- **Rate limiter:** caps how many calls per second are allowed through.
- **Fallback:** a degraded answer when the call fails (cached data, default value).
- **Load shedding:** a overloaded service deliberately rejects excess requests (e.g. HTTP 503) to stay healthy for the rest.
- **Fault injection:** deliberately breaking things in tests to prove the protections work.

**The live scenario**
A checkout service calls a pricing service at about 500 requests/second. Pricing slows from 50 ms to 30 s. Checkout has no timeouts, so each request holds a thread. Within a minute all 200 threads are stuck and checkout is down, though only pricing was sick. Clients retry, tripling the load on pricing, so it can't recover. A 2-second timeout, a breaker, a bulkhead and a cached-price fallback would have kept checkout up.

**What the interviewer is really checking**
Whether you know these patterns work as a set, in the right order, and that retries can make an outage worse. Also whether you know which ones apply to every call and which belong on the server side.

**How I answer it**
1. **Timeout on every call.** Set connect and read timeouts on the HTTP client. This is the minimum rule, because a call without one can hang forever.
2. **Retry only idempotent calls, with exponential backoff and jitter, and a small cap (2-3 attempts).** Retrying non-idempotent calls can double-charge. Jitter prevents synchronised retry storms.
3. **Circuit breaker.** It stops you hammering a dependency that is clearly failing and frees your threads quickly.
4. **Bulkhead per dependency.** It isolates the damage to one failing dependency.
5. **Rate limiter** protects a dependency from you (or you from callers). **Load shedding** is mainly the server's job: reject early when overloaded.
6. **Fallback** for a degraded but useful response.
7. **Order matters.** In Resilience4j the default nesting, outermost first, is:
```
Retry( CircuitBreaker( RateLimiter( TimeLimiter( Bulkhead( call )))))
```
Retry is outside so each attempt is counted by the breaker. Don't retry when the breaker is open. Wrap a fallback around the whole chain.
8. **Prove it** with fault injection (Chaos Monkey, Toxiproxy): add latency, drop connections, and check the system degrades gracefully.

**Trade-offs and what can go wrong**
- Retries multiply load (3 attempts across 3 layers = 27 calls). Retry at one layer only.
- Timeouts too short cause false failures. Too long defeats the purpose. Base them on the callee's p99.
- Breaker thresholds that are too sensitive flap open and closed.
- Fallbacks can hide real problems or serve stale data. Make them visible in metrics.
- TimeLimiter works with async calls. For blocking calls, rely on client timeouts.
- More patterns mean more configuration to tune and test.

**How I'd monitor it**
- Breaker state and transitions, plus the failure rate (Resilience4j metrics via Micrometer, shown in Grafana).
- Retry counts, timeout counts, bulkhead rejections, fallback usage, p95/p99 latency per dependency.
- Splunk: search for "CallNotPermittedException" or "TimeoutException" by service and correlation id.
- Alert when a breaker stays open or fallback rate climbs.

**Follow-ups to expect**
- *Why not retry POST requests?* -> It may have succeeded before the failure, so retrying can duplicate it. Retry only with an idempotency key.
- *What is a retry storm?* -> Many clients retrying at once multiply load on a struggling service. Backoff, jitter, caps and breakers prevent it.
- *Circuit breaker vs bulkhead?* -> The breaker stops calls to a failing service. The bulkhead limits resources one dependency can consume.

**60-second answer**
On every remote call I set a timeout first, because a call that can hang will eventually use up all my threads. I retry only idempotent calls, with exponential backoff and jitter and a small limit. A circuit breaker stops me calling a dependency that is failing, and a bulkhead keeps one slow dependency from taking all my threads. Rate limiting and load shedding protect services from overload, and a fallback gives a degraded answer. Order matters: retry outside, then breaker, rate limiter, time limit and bulkhead, with the fallback around everything. I verify it with fault injection like Toxiproxy and watch breaker state, timeouts and fallback rates.

### Q8 [mid] What is service discovery and how does it work in Kubernetes?
tags: microservices, service-discovery, kubernetes, dns, load-balancing, basics

**Start here: the concepts**
- **Service discovery:** the way one service finds the network address of another. Addresses change constantly in a cloud, because instances start, crash, scale and move. Hard-coding an IP breaks, so callers use a *name* and something resolves it to a live address.
- **Instance:** one running copy of a service. In Kubernetes that is a *pod*.
- **Pod:** the smallest unit Kubernetes runs, usually one container. Each pod gets its own IP, and that IP changes when the pod is replaced.
- **Kubernetes `Service`:** a stable front door for a group of pods. It has a fixed virtual IP (the ClusterIP) and a fixed name, and it picks its pods by *labels*.
- **DNS:** the phone book that turns names into IPs. Kubernetes runs one inside the cluster (CoreDNS). A Service such as `orders` in namespace `default` is reachable as `orders.default.svc` (fully `orders.default.svc.cluster.local`). Inside the same namespace, plain `orders` works.
- **Readiness probe:** a health check Kubernetes runs on each pod. Only pods that pass it receive traffic.
- **Load balancing:** spreading requests across several instances. *Client-side* means the caller keeps a list of instances and picks one (Spring Cloud LoadBalancer). *Server-side* means something in the middle picks, which is what a Kubernetes Service does.
- **Eureka/Consul:** registries where instances register themselves and callers look them up. They are needed where the platform gives no built-in naming, such as plain VMs.

**The live scenario**
A team ran 12 services on VMs with IPs in config files. Each release changed a few addresses, and about 5% of requests failed for 10 minutes while configs caught up. After moving to Kubernetes, the checkout service called `http://orders/api/orders`. During a rollout from 6 old pods to 6 new ones, errors stayed near zero because new pods joined the Service only after passing readiness, and old pods were removed from it before they stopped.

**What the interviewer is really checking**
Whether you understand that discovery means "name in, healthy address out", and whether you know Kubernetes already provides it, so you don't add Eureka without a reason.

**How I answer it**
1. **Define the problem.** Instance IPs are temporary, so callers must use a stable name. A registry or the platform maps that name to live instances.
2. **Explain the Kubernetes mechanism.** A `Service` selects pods by label and gets a stable ClusterIP and a DNS name from CoreDNS. The caller just uses the name:
   `http://orders/api/orders`
3. **Explain readiness.** Kubernetes tracks the pods behind a Service (in EndpointSlices) and includes only those passing readiness checks. This is what makes rolling deploys safe, so the readiness probe must be accurate.
4. **Explain load balancing.** The Service spreads traffic across ready pods (done by kube-proxy on each node). The app needs no discovery code or library.
5. **Say when you'd still use client-side discovery.** Outside Kubernetes, or across clusters or VMs, use Eureka/Consul with Spring Cloud LoadBalancer. Inside Kubernetes it is usually redundant, and running both adds a second source of truth that can go stale.

**Trade-offs and what can go wrong**
- Kubernetes Service balancing happens per *connection*. Long-lived HTTP/2 or gRPC connections can pin most traffic to a few pods. Fix with a headless Service plus client-side balancing, or a service mesh or L7 proxy.
- A weak readiness probe sends traffic to pods that aren't ready, causing errors during deploys.
- DNS only works inside the cluster. Cross-cluster calls need an ingress, a gateway or a mesh.
- Callers using a client-side cache of addresses (or JVM DNS caching) can keep hitting dead pods.
- Registries such as Eureka favour availability and can return stale entries.

**How I'd monitor it**
- `kubectl get endpointslices` and `kubectl get pods`: do the ready pods match what you expect?
- CoreDNS metrics (request latency, error response codes) in Prometheus.
- Per-pod request rate, to spot skewed load balancing.
- Splunk searches for `UnknownHostException`, `Connection refused` and `no route to host`, grouped by service and time. Alert when they spike after a deploy.
- Readiness-failure and restart counts per deployment.

**Follow-ups to expect**
- *What is a headless Service?* -> One with `clusterIP: None`. DNS returns the individual pod IPs instead of one virtual IP, so the client can balance itself, which is useful for gRPC or stateful sets.
- *Why can gRPC traffic be uneven behind a Service?* -> It keeps one long HTTP/2 connection, and Kubernetes balances per connection, so one pod can get most requests.
- *How do you reach a service in another namespace?* -> Use `service.namespace.svc`, for example `orders.prod.svc`.

**60-second answer**
Service discovery is how one service finds a healthy instance of another, using a stable name instead of an IP that changes. In Kubernetes, a `Service` gives a pod group a fixed virtual IP and a DNS name like `orders.default.svc`. It only sends traffic to pods that pass their readiness check, and it spreads requests across them. So we usually don't need Eureka or Consul, and the app just calls the name. Client-side load balancing, like Spring Cloud LoadBalancer, matters for non-Kubernetes setups or for headless Services. The main caveat is that balancing is per connection, so long-lived gRPC connections can skew load. I'd watch endpoints, CoreDNS errors and per-pod traffic.

### Q9 [mid] What is an API Gateway vs BFF vs Service Mesh?
tags: api-gateway, bff, service-mesh, istio, east-west-traffic, microservices, basics

**Start here: the concepts**
- **Microservices:** many small services, each owning one business area. Clients and services must now talk across a network instead of through method calls.
- **North-south vs east-west traffic:** north-south is traffic coming from outside (browser, mobile app) into your system. East-west is traffic between your own services inside it. The three tools below mostly differ in which traffic they handle.
- **API Gateway:** a single entry point for external traffic. It checks identity (authentication), routes each request to the right service, and applies limits (rate limiting). It exists so every service doesn't reimplement these things and clients don't need to know where each service lives.
- **BFF (Backend for Frontend):** a small backend built for one type of client (web BFF, mobile BFF). It calls several services and returns exactly the data that screen needs. It exists because mobile and web need different payload sizes and shapes.
- **Service mesh (Istio, Linkerd):** infrastructure that manages service-to-service calls. A small proxy (a "sidecar") runs next to each service instance and intercepts its network traffic. A control plane configures all the proxies. Some meshes now offer sidecar-less modes, but the idea is the same.
- **mTLS:** mutual TLS. Both sides prove their identity and the traffic is encrypted, so internal calls can't be spoofed or read.
- **Traffic shifting:** sending a percentage of requests to a new version (for example 5%) for safe rollouts.
- **Telemetry:** metrics, traces and logs about calls.

**The live scenario**
A retail company has about 40 services, a web app and a mobile app. The mobile home screen makes 7 separate calls over a slow 4G connection and takes around 3 seconds to load. Each team validates tokens differently, and one service had no rate limiting and was overwhelmed by a buggy client. Internally, security wants all service-to-service traffic encrypted, and the teams are tired of every service writing its own retry code. The fix was three layers, each solving a different problem.

**What the interviewer is really checking**
Whether you know these are different tools for different jobs (outside traffic, per-client shaping, inside traffic), that they complement each other, and that you understand the cost of each, especially the mesh.

**How I answer it**
1. **Define by traffic direction.** Gateway and BFF face outward (north-south). The mesh handles inward service-to-service calls (east-west). This shows the three don't compete.
2. **Gateway first.** Put cross-cutting edge concerns in one place: authentication, routing, rate limits, TLS termination. The reason is consistency, because one place to fix and audit. Keep business logic out of it, or it becomes a bottleneck every team must change.
3. **Add a BFF per client type when screens differ.** The mobile BFF makes the 7 calls inside the data centre (fast) and returns one small response. The reason is to stop clients doing orchestration over slow networks. Ideally the team that owns the UI owns its BFF.
4. **Add a mesh only when east-west problems appear.** Sidecars give mTLS, retries, timeouts, traffic shifting and telemetry without changing application code. The reason is uniform behaviour across languages and teams.
5. **Typical layout:** client → gateway → BFF → services, with the mesh wrapping the calls between services (and often the gateway-to-service hop).

**Trade-offs and what can go wrong**
- Gateway: a single point of failure if not run redundantly, and a bottleneck if it accumulates business logic.
- BFF: more code to maintain, and duplicated logic across BFFs if you're careless.
- Mesh: significant operational complexity (extra proxies using CPU and memory, added latency per hop, hard upgrades, harder debugging). It is not worth it for 5 services.
- Mesh retries can multiply load (a retry storm) when a service is already struggling. Retries are only safe for idempotent calls, and you still need timeouts and circuit breakers.
- Common mistake: calling a gateway a mesh, or putting orchestration logic in the gateway.

**How I'd monitor it**
- Gateway: request rate, error rate (4xx/5xx), p95/p99 latency, rate-limited request count, and upstream health.
- BFF: latency per downstream call and fan-out time.
- Mesh: per-service success rate, retry counts, circuit-breaker trips, mTLS coverage, and sidecar CPU/memory.
- Pass a correlation id through every hop, then search it in Splunk to follow one request across gateway, BFF and services. Alert on error-rate and latency SLO breaches.

**Follow-ups to expect**
- *Does a service mesh replace an API gateway?* -> No. The gateway handles external clients, with public API concerns such as auth and rate limits. The mesh handles internal traffic. Some meshes include an ingress component, but the roles differ.
- *Why not one generic API for all clients?* -> Mobile needs smaller, fewer responses than web. A single API either over-fetches for one client or forces many round trips.
- *Can you do retries and circuit breaking without a mesh?* -> Yes, with libraries such as Resilience4j in each service. That is fine for a few services or one language. A mesh helps when you have many services in many languages.

**60-second answer**
These solve different problems. An API Gateway is the single front door for external traffic: it handles authentication, routing and rate limiting so each service doesn't. A BFF is a backend built for one client type, like mobile or web. It combines several service calls into one response shaped for that screen. A service mesh, like Istio or Linkerd, handles traffic between services inside the system. It uses sidecar proxies to give mTLS, retries, traffic shifting and telemetry without changing code. They work together: client to gateway to BFF to services, with the mesh underneath. The cost is complexity, especially for the mesh, so I'd adopt it only when I have many services and real east-west problems.

### Q10 [mid] How do you handle configuration and secrets across services?
tags: microservices, configuration, secrets, kubernetes, vault, spring-cloud-config, basics

**Start here: the concepts**
- **Configuration:** values that change between environments without changing code, such as a database URL, a timeout or a thread-pool size. It is kept outside the code so one build can run in dev, test and production.
- **Externalised config:** the app reads these values at startup (or at runtime) from the environment or a config service, not from a file baked into the build. This exists so a config change does not need a rebuild.
- **ConfigMap:** a Kubernetes object that holds non-sensitive key-value settings and hands them to a pod as environment variables or files.
- **Spring Cloud Config:** a server that serves Spring Boot properties, usually from a Git repository, to many services. **AWS Parameter Store** and **AppConfig** are AWS services that store and deliver config values. AppConfig adds controlled, validated rollout of changes.
- **Secret:** a value that gives access if stolen, such as a password, API key or certificate. It needs stricter handling than ordinary config.
- **Vault / AWS Secrets Manager:** dedicated secret stores. They encrypt secrets, control who can read them, keep an audit log and can rotate them.
- **Injected at runtime:** the secret is fetched or mounted when the pod starts, so it is never stored in the image or the repository.
- **Rotation:** replacing a secret regularly (or after a leak) so a stolen copy stops working.
- **Overlay (Kustomize/Helm):** a base set of deployment files plus small per-environment differences, such as replicas or URLs. This avoids copy-pasting whole files for each environment.
- **Feature flag:** a runtime on/off switch for a behaviour, so you can enable or disable a feature without redeploying.

**The live scenario**
A team runs 40 services. A developer commits a payment-gateway API key to Git "temporarily". Three weeks later, a security scan finds it in history, and the key is also baked into 12 old container images. Rotating it means rebuilding and redeploying 5 services over a weekend, with a 2-hour payment outage when one service was missed. The fix was to move the key to a secret store, inject it at startup and rotate it on a schedule. The next rotation took 10 minutes and caused no outage.

**What the interviewer is really checking**
That you separate config from secrets, keep both out of code and images, and understand rotation, per-environment differences and runtime toggles. Mid-level candidates should also know that a Kubernetes Secret alone is not real protection.

**How I answer it**
1. **Build once, configure outside.** The same image runs in every environment, and the environment supplies the values. This way what you tested is exactly what you deploy.
2. **Keep ordinary config in ConfigMaps, Spring Cloud Config or Parameter Store/AppConfig.** Choose by platform: ConfigMaps on Kubernetes, Spring Cloud Config for shared Spring properties with Git history, AWS services on AWS. Changes are then versioned and reviewable.
3. **Keep secrets in Vault or Secrets Manager.** They give encryption, access control, auditing and rotation. A plain Kubernetes Secret is only base64-encoded, not encrypted by default, so enable encryption at rest and tight RBAC (role-based access control), or sync from the secret store.
4. **Inject at runtime, never bake in.** Mount the secret as an environment variable or file when the pod starts, using the service's own identity to authorise access:
```yaml
env:
- name: DB_PASSWORD
  valueFrom: { secretKeyRef: { name: orders-db, key: password } }
```
5. **Rotate, and design for it.** Rotation only helps if services can pick up new values, by re-reading, refreshing or restarting. Prefer short-lived credentials where the store supports them.
6. **Use overlays per environment.** A Kustomize or Helm base plus small overrides keeps dev, test and production consistent, and the overrides live in Git. Never put secrets in those files.
7. **Use feature flags for runtime toggles.** They separate deploying code from releasing a feature, so you can switch a feature off in seconds without a rollback.
8. **Keep secrets out of Git and images.** Add scanning in CI to catch accidents. If one leaks, treat it as compromised and rotate it, because deleting the commit is not enough.

**Trade-offs and what can go wrong**
- The secret store becomes a critical dependency: if it is down at startup, pods can fail to start. Use caching and high availability.
- Config drift: values edited by hand in one environment but not in Git.
- Changing config at runtime can break all services at once. Roll out gradually and validate.
- Spring beans normally read properties at startup, so a refresh needs explicit support (for example `@RefreshScope`) or a restart.
- Logging full config objects or environment dumps leaks secrets.
- Feature flags left in the code forever become hidden complexity.

**How I'd monitor it**
- Alerts from secret scanning in CI and on repositories.
- Audit logs from Vault or Secrets Manager: who read which secret, and unusual access.
- Rotation age per secret, alerting when it is overdue.
- Startup failure and restart counts after config or secret changes.
- A Splunk search for patterns like `password=` or `apikey` in application logs.
- Config version in logs or metrics, to link an incident to a change.

**Follow-ups to expect**
- *Is a Kubernetes Secret safe?* -> Not by itself. It is base64-encoded. Enable encryption at rest, restrict access with RBAC, or sync from Vault or Secrets Manager.
- *How do you change config without restarting?* -> Use a refresh mechanism, such as Spring's refresh scope or AppConfig polling, for values that are safe to change live. Restart for the rest.
- *A secret leaked. What now?* -> Revoke and rotate immediately, check audit logs for misuse, then fix the cause. Removing it from Git history is not enough.

**60-second answer**
I build the image once and keep configuration outside it, so the same artifact runs in every environment. Ordinary settings live in ConfigMaps, Spring Cloud Config or Parameter Store/AppConfig. Secrets live in Vault or Secrets Manager and are injected at runtime, with rotation. Nothing sensitive goes into Git or an image, and CI scans to enforce that. I use Kustomize or Helm overlays for per-environment differences and feature flags to turn behaviour on or off without redeploying. I'm careful that a plain Kubernetes Secret is only base64-encoded, so I add encryption and access control. I monitor secret age, access audit logs and startup failures after changes.

### Q11 [senior] How do you version events and APIs between services?
tags: microservices, api-versioning, event-versioning, schema-registry, avro, contract-testing, basics

**Start here: the concepts**
- **Contract**: the agreed shape of a message or API response (field names, types, meaning). Producer and consumer are deployed separately, so the contract is all they share.
- **Breaking change**: a change that makes an existing consumer fail or misbehave. Examples: removing or renaming a field, changing a type, or changing what a field means.
- **Additive change**: adding a new optional field. Old consumers can ignore it, so it is normally safe.
- **Schema**: a formal description of a message (Avro, Protobuf or JSON Schema). It lets tools check a change before it ships.
- **Schema registry**: a central service that stores every schema version and rejects a new version that breaks the compatibility rule you chose.
- **BACKWARD compatibility**: consumers using the *new* schema can still read data written with the *old* one. In Avro, a new field needs a default value to satisfy this. Use BACKWARD_TRANSITIVE to check against all earlier versions, not just the latest. This matters because Kafka keeps old events that can be replayed.
- **Tolerant reader**: a consumer that reads only the fields it needs and ignores unknown ones, so additions never break it.
- **Dual publishing / side-by-side versions**: during a migration, the producer emits both the old and new versions (for events, usually on separate topics). For APIs, v1 and v2 run together.
- **Consumer-driven contract test** (for example Pact or Spring Cloud Contract): each consumer writes down what it relies on, and the producer's build fails if a change breaks that.

**The live scenario**
An Order service publishes `OrderPlaced` to Kafka, and 9 teams consume it. One team renames `customerId` to `clientId` and deploys on Friday. Billing and Shipping start throwing deserialization errors, consumer lag grows to 400k messages in 20 minutes, and about 3% of orders are delayed. The rename was safe inside the producer team's code, but the contract belongs to everyone who reads it.

**What the interviewer is really checking**
Whether you know that services deploy independently, so you can't change producer and consumers together. They want to see compatibility rules, automated enforcement, and a safe migration path for the day a breaking change is truly unavoidable.

**How I answer it**
1. **Treat the message or API as a public contract.** Many teams depend on it, and you cannot coordinate them all to deploy at the same moment.
2. **Make add-only changes.** New fields are optional or have defaults. Never repurpose a field (same name, new meaning), because old consumers will silently misread it and nothing fails loudly. In Protobuf, never reuse a field number.
3. **Enforce rules with a schema registry.** Set compatibility to BACKWARD (or BACKWARD_TRANSITIVE). The CI build registers the new schema as a check, and a breaking one fails before it reaches production. Humans forget, so the registry does the checking.
4. **Write tolerant consumers.** They ignore unknown fields and don't fail on new enum values they haven't seen. Then step 2 stays safe in practice.
5. **Add consumer-driven contract tests.** Schema checks catch structural breaks, but not a consumer depending on behaviour such as "this field is never null".
6. **For a truly breaking change, run old and new side by side.** Publish both versions (for example `orders.v1` and `orders.v2`, or `/v1` and `/v2` endpoints). Move consumers one by one, watch v1 traffic fall to zero, then retire v1 with a announced deadline. Dual publishing is temporary and has a cost, so set an end date.
7. **Expand, then contract.** Add the new field, migrate consumers, and only then remove the old field.

**Trade-offs and what can go wrong**
- Dual publishing can cause duplicates for consumers that subscribe to both, and the two versions can drift apart.
- Old versions that never get retired become permanent maintenance burden.
- Replaying old Kafka data means consumers must handle every historical version.
- BACKWARD alone does not protect old consumers from new producers. Use FULL if both directions matter.
- A registry catches structure, not meaning.

**How I'd monitor it**
- Schema registry compatibility failures in CI.
- Deserialization error rate and dead-letter topic counts.
- Consumer lag per group after each producer deploy.
- Gateway traffic per API version, to know when v1 is safe to remove.
- A Splunk search on deserialization or unknown-field exceptions, grouped by service and version, with an alert on a spike.

**Follow-ups to expect**
- *Why not just URL-version everything?* -> It forces maintaining many copies. Additive evolution keeps one version most of the time, and a new version is reserved for real breaks.
- *BACKWARD vs FORWARD vs FULL?* -> BACKWARD: new readers handle old data. FORWARD: old readers handle new data. FULL: both.
- *How do you remove a field safely?* -> Deprecate it, confirm through contract tests and metrics that no consumer reads it, then remove it in a later version.

**60-second answer**
Producers and consumers deploy independently, so I treat every event and API as a contract. I make only additive changes, such as new optional fields with defaults, and I never rename or repurpose a field. I store schemas in a registry with BACKWARD compatibility, ideally transitive because Kafka data can be replayed, so CI blocks breaking changes. Consumers are tolerant readers that ignore unknown fields, and consumer-driven contract tests catch behaviour the schema can't. If a breaking change is unavoidable, I publish old and new versions side by side, migrate consumers one by one, watch old-version traffic drop to zero, and then retire it. I watch deserialization errors, lag and per-version traffic to prove it works.

### Q12 [senior] How do you test microservices?
tags: microservices, testing, testcontainers, contract-testing, consumer-driven-contracts, test-pyramid, basics

**Start here: the concepts**
- **Test pyramid:** a way to balance tests by cost. Many small, fast, cheap tests at the bottom; fewer slow, expensive, fragile ones at the top. It exists because slow tests delay feedback and fragile tests get ignored.
- **Unit test:** tests one class or method in memory, with no network or database. It runs in milliseconds and checks business rules.
- **Service-level integration test:** starts one service and checks it against real infrastructure (database, Kafka). It catches problems that mocks hide, such as wrong SQL, serialization errors and bad Kafka config.
- **Testcontainers:** a Java library that starts throwaway Docker containers (a real database or Kafka broker) for the test and deletes them afterwards. It needs Docker on the build machine. It replaces in-memory fakes, which behave differently from the real thing.
- **Contract test (consumer-driven):** the *consumer* service writes down what it expects from a *provider* service (fields, types, status codes). The provider's build checks it still satisfies those expectations. Tools include Pact and Spring Cloud Contract. It exists so two teams can change independently without breaking each other, and without starting both services together.
- **End-to-end (E2E) test:** drives the whole system through its public entry point in a staging environment. It is realistic but slow and flaky, so keep only a few, covering critical journeys.
- **Load test:** sends heavy traffic to check latency and capacity.
- **Chaos test:** deliberately breaks things (kills an instance, adds latency) to prove timeouts, retries and circuit breakers work.

**The live scenario**
A team of 8 services ran 400 E2E tests that took 90 minutes and failed randomly about 15% of the time. Developers re-ran the build until it went green. One day the Orders team renamed a JSON field, `customerId` to `custId`. Every test passed, but Billing broke in production at 9 a.m. and about 2% of orders failed for 40 minutes. The team then moved most checks down the pyramid, added contract tests, and cut the pipeline to 12 minutes.

**What the interviewer is really checking**
Whether you know that testing across service boundaries is the hard part, and whether you can get confidence without one giant, slow, flaky test environment.

**How I answer it**
1. **Unit tests first, in large numbers.** They are fast and pinpoint the failure, so developers get feedback in seconds.
2. **Integration tests per service with Testcontainers.** Each service is tested alone against a real database and real Kafka. This finds query, mapping and serialization bugs that mocks cannot, while keeping the test independent of other teams' services.
   ```java
   @Container static KafkaContainer kafka = new KafkaContainer(/* image tag */);
   ```
3. **Consumer-driven contract tests between services.** The consumer publishes its expectations and the provider's pipeline verifies them. A breaking change like the field rename fails the provider's build, before deployment.
4. **A handful of E2E tests in staging.** Cover only the critical journeys (for example place order, pay, ship). Every extra E2E test adds flakiness and maintenance cost, so don't run them for every change.
5. **Load and chaos tests on a schedule or before big releases.** Functional tests don't show how the system behaves under pressure or partial failure.
6. **Verify in production too.** Use canary releases and synthetic checks, because no staging environment matches production exactly.

**Trade-offs and what can go wrong**
- Testcontainers slows builds (container start-up) and needs Docker in CI. Reuse containers within a test suite.
- Contract tests only cover what consumers write down. Stale or missing contracts give false confidence.
- Too many E2E tests lead to flaky pipelines that teams stop trusting.
- Staging data and scale differ from production, so passing there isn't proof.
- Mocking everything gives fast but meaningless tests.

**How I'd monitor it**
- Pipeline duration and flaky-test rate (failures that pass on re-run).
- Contract verification failures per provider build, which are the breaking changes you caught early.
- Escaped defects: production incidents that tests should have caught.
- After each deploy, the error rate and latency per service, and a Splunk search on the correlation id of failed requests.
- Synthetic checks on critical journeys, with alerts.

**Follow-ups to expect**
- *Why not just run full E2E for every change?* -> It is slow, flaky and hard to debug. Contract tests plus per-service integration tests give most of the confidence at a fraction of the cost.
- *How do contract tests differ from integration tests?* -> Integration tests check a service against real infrastructure. Contract tests check the agreement between two services' APIs or messages without running both together.
- *How do you test Kafka-based flows?* -> Use a Testcontainers Kafka broker for producer and consumer tests, contract-test the message schema, and test that consumers are idempotent (processing a duplicate message is safe).

**60-second answer**
I use a test pyramid. Most tests are fast unit tests. On top of those, each service has integration tests against a real database and Kafka using Testcontainers, so mocks don't hide real bugs. Between services I use consumer-driven contract tests, where the consumer states what it needs and the provider's build checks it, so a breaking change is caught before release. I keep only a few end-to-end tests in staging for critical journeys, because they are slow and flaky. I also run load and chaos tests to prove performance and resilience, and watch error rates after each deploy, since staging never matches production.

### Q13 [senior] How do you do deployments safely?
tags: deployment, canary, blue-green, feature-flags, expand-contract, rollback, slo, basics

**Start here: the concepts**
- **CI (continuous integration):** a server that builds and tests the code on every commit. It exists so that a broken build is caught in minutes, not on release day.
- **Immutable image:** a container image built once and never changed. The same image goes to staging and production, and only configuration differs. This removes "it worked in staging" surprises caused by rebuilding or patching servers by hand.
- **Staging:** a production-like environment where we try the release before real users see it.
- **Smoke test:** a few fast checks that the app starts and its main paths work (for example, "can I log in and place an order?").
- **Contract test:** a check that a service still honours the request and response shapes that its callers (or the messages its consumers) expect. It catches breaking API changes without running the whole system.
- **Canary release:** the new version gets a small share of real traffic (say 5%) while the old version serves the rest. If it looks healthy, the share grows.
- **Blue/green:** two full environments. Blue is live and green holds the new version. Once green is verified, traffic switches over, and switching back is the rollback.
- **SLO (service level objective):** a measurable target, such as "99.9% of requests succeed and p99 latency is under 300 ms". An SLO breach is an objective trigger for rollback, so nobody has to argue about it.
- **Feature flag:** a runtime switch that turns a feature on or off without redeploying. It separates **deploy** (code is in production) from **release** (users see it).
- **Expand/contract (database):** change the schema in compatible steps. Expand by adding the new column or table. Run old and new code together. Migrate the data. Contract by removing the old structure later. It exists because during a rollout both versions talk to the same database.

**The live scenario**
A payments service handles about 2,000 requests per second. The team deployed to every instance at once at 2 pm. A new query was slow, and the error rate rose from 0.1% to 8%. It took 12 minutes to notice and roll back, which meant roughly 100,000 failed requests. They moved to canary releases. The next bad release hit only 5% of traffic, the SLO alert fired, and automatic rollback happened in about 3 minutes. That limited the damage to roughly 1,400 failed requests.

**What the interviewer is really checking**
Whether you treat deployment as risk reduction: small blast radius, automatic detection, fast reversal. They also want to see that you know the database is the hard part of rolling back.

**How I answer it**
1. **CI builds one immutable image.** The artifact tested is the artifact shipped, so there is no drift between environments.
2. **Deploy to staging and run smoke and contract tests.** Contract tests matter in microservices because you cannot test every service combination together. They catch a broken API before a caller does.
3. **Release by canary or blue/green, not all at once.** Canary limits the blast radius to a small share of users. Blue/green gives an instant switch back but needs double capacity. I pick canary for gradual confidence and blue/green when I need an atomic cutover.
4. **Automate rollback on SLO breach.** Humans are slow at 2 am. The pipeline compares error rate and latency of the new version against the old one and reverts by itself.
5. **Use feature flags to decouple deploy from release.** Ship the code switched off, then enable it for 1%, then 10%, then everyone. If the feature is bad, turning the flag off takes seconds and needs no redeploy.
6. **Change the database with expand/contract.** Add the new column first, deploy code that works with both shapes, backfill data, switch reads, and drop the old column in a later release. Old and new versions can then run side by side, and rolling back the code never hits a schema it cannot read.

**Trade-offs and what can go wrong**
- Canary and blue/green cost more: extra capacity, traffic-routing tooling, and a more complex pipeline.
- A canary only helps if it gets enough traffic and the metrics are good enough to show the problem. A 5% slice of a quiet service proves little.
- Stale feature flags pile up as hidden complexity, so remove them after rollout.
- Expand/contract takes several releases for one change. Destructive migrations (dropping or renaming in one step) make rollback impossible.
- Message formats on Kafka or queues must also be backward compatible, because old and new consumers run together.

**How I'd monitor it**
Compare canary and baseline on error rate, p99 latency, and saturation (CPU, memory, connection pools). Watch business metrics such as orders per minute. Alert on SLO burn rate. Search logs in Splunk by version tag and correlation id to isolate the new version's errors. Track deployment frequency and rollback rate as health indicators of the process.

**Follow-ups to expect**
- *Canary or blue/green?* -> Canary gives gradual, real-traffic validation at low cost. Blue/green gives an instant, all-or-nothing switch and rollback but needs duplicate capacity.
- *How do you roll back when a migration has run?* -> Because of expand/contract, the old code still works with the expanded schema, so only the code is rolled back and the data is untouched.
- *How do you keep consumers safe during rollout?* -> Make changes backward compatible, use contract tests, and keep old and new versions able to read each other's messages.

**60-second answer**
I never release to everyone at once. CI builds one immutable image, which I deploy to staging and check with smoke and contract tests. In production I use a canary or blue/green release, so only a small share of users, or an instantly reversible environment, is exposed. The pipeline watches SLOs like error rate and latency and rolls back automatically if they break. I use feature flags so that deploying code and releasing a feature are separate, and I can switch a feature off in seconds. For database changes I use expand/contract, so old and new versions work together and rollback stays safe. The cost is extra capacity and pipeline complexity, but it keeps incidents small.

### Q14 [senior] How do you decompose a monolith (strangler fig)?
tags: microservices, strangler-fig, monolith-migration, api-gateway, cdc, data-ownership, basics

**Start here: the concepts**
- **Monolith:** one deployable application holding many business capabilities (orders, billing, catalog) and usually one shared database. It is simple at first but gets slow to change and risky to release as it grows.
- **Strangler fig:** named after a vine that grows around a tree until it replaces it. You build new services around the monolith, move work to them piece by piece, and the old code shrinks until you can remove it.
- **Facade / API gateway:** a single entry point in front of the monolith. Callers talk only to it, and it decides per request whether the monolith or a new service answers. This lets you switch capabilities without clients noticing.
- **Bounded context:** a part of the business with its own vocabulary and rules, such as "Billing". Good service boundaries follow these, not technical layers.
- **Data ownership:** each service is the only writer of its data. Shared tables recreate the coupling you are trying to escape.
- **CDC (change data capture):** reads the database's change log and publishes each row change as an event. It lets data flow to a new service without editing monolith code.
- **Big-bang rewrite:** stopping to rebuild everything and switching over once. It is risky because nothing is proven in production until the end.

**The live scenario**
An e-commerce monolith (illustrative: 400k lines, one release every 3 weeks) handles 2,000 requests/second at peak. The notification and pricing code changes daily, but every change forces a full regression test and deploy. A previous "rewrite everything in 12 months" plan was cancelled after 9 months with nothing live. The team now extracts **Notifications** first: clear boundary, frequent changes, low financial risk. They route 5% of traffic to it, compare results, then raise it to 100%.

**What the interviewer is really checking**
Whether you migrate incrementally and safely: reversible steps, data handled deliberately, no big bang. Also whether you know the hard part is the data, not the code.

**How I answer it**
1. **Find the seams.** Map bounded contexts and dependencies in the monolith. Boundaries show where cuts are cheap and where the code is tangled.
2. **Pick the first candidate.** Choose a module with clear boundaries and a high change rate. Clear boundaries make extraction feasible. High change rate means the team gets value quickly. Avoid the riskiest core (payments) first, because you are still learning.
3. **Put a facade/gateway in front.** All traffic goes through it, initially to the monolith only. This adds one hop but gives you a switch.
4. **Build the new service for one capability.** Keep the monolith running throughout, so you can roll back by flipping the route.
5. **Handle data.** The new service gets its own store. Sync from the monolith database with events or CDC until the new service becomes the source of truth. Then stop the monolith writing that data. Add an anti-corruption layer so the monolith's model does not leak into the new service.
6. **Shift traffic gradually.** Use a percentage or canary route, optionally with shadow traffic (copies of requests whose responses are discarded) to compare outputs. Increase only when results match.
7. **Delete the old code.** Once 100% of traffic is moved and stable, remove the module and its tables. If you skip this, you get two systems to maintain.
8. **Repeat.** Each slice teaches you something. Avoid a big-bang rewrite because value arrives early and risk stays small.

**Trade-offs and what can go wrong**
- Two systems run in parallel for months, which means more infrastructure and operations.
- Data sync is eventually consistent, so reads can briefly be stale. Dual writes (writing to both stores in app code) can diverge, so prefer CDC or an outbox.
- A "distributed monolith": services still share a database or call each other chains synchronously, giving the costs of microservices without the benefits.
- The migration stalls at 70% and never finishes. Plan the deletion and give it an owner.
- Debugging now crosses services, so correlation ids and tracing are needed from day one.

**How I'd monitor it**
- Per-route metrics at the gateway: traffic split %, error rate, p95/p99 latency, old vs new.
- Response comparison results from shadow traffic (mismatch count).
- CDC/event consumer lag and sync error counts.
- Splunk search on a correlation id (for example `correlationId=abc123`) across gateway, monolith and service logs.
- Alert on error-rate regression after each traffic increase, and keep a one-step rollback.

**Follow-ups to expect**
- *How do you handle a table both the monolith and new service need?* -> Make one the owner, sync to the other via CDC or events, and move writes to the new service step by step. Never keep long-term shared write access.
- *Why not rewrite from scratch?* -> It delivers no value until the end, the old system keeps changing meanwhile, and a failed cutover is hard to undo.
- *How do you roll back?* -> Flip the gateway route to the monolith. That works only if the monolith's data stayed correct, so keep sync two-way or delay cutting the old data path.

**60-second answer**
I use the strangler fig pattern. I put a gateway in front of the monolith so I can choose, per capability, whether the old or new code answers. I pick a first module with clear boundaries and a high change rate, build it as a service with its own data, and keep the monolith running. I sync data using events or CDC, then route traffic gradually, starting with a small percentage and comparing results. When all traffic has moved and is stable, I delete the old code and repeat. This avoids a big-bang rewrite, keeps rollback easy, and delivers value early. The costs are running two systems for a while, eventual consistency, and harder debugging, so I add tracing and correlation ids from the start.

### Q15 [senior] What are the signs you've built a "distributed monolith"?
tags: microservices, distributed-monolith, bounded-context, coupling, data-ownership, resilience, basics

**Start here: the concepts**
- **Monolith:** one application deployed as one unit. Its weakness is that everything changes and fails together. Its strength is simplicity: in-process calls and one database transaction.
- **Microservices:** many small services, each deployable on its own. The goal is that a team can change, release and scale its service without asking anyone else.
- **Distributed monolith:** you split the code into services but kept the coupling. You pay for the network, with latency, partial failure and harder debugging, and you get none of the independence.
- **Bounded context:** a business area (Billing, Inventory, Shipping) with its own vocabulary and rules. Good service boundaries follow these areas, not technical layers.
- **Data ownership:** only one service reads and writes a given table. Others ask it through an API or events. This lets the owner change its schema freely.
- **Synchronous call chain:** A calls B, which calls C, which calls D, and each waits for the next. Latency adds up and availability multiplies down.
- **Event:** a message saying "something happened" (OrderPlaced). Consumers react in their own time, so the producer does not wait.
- **Cascading failure:** one slow or dead service makes its callers pile up waiting, and they fail too.

**The live scenario**
A retail company has 25 "microservices". A release happens every second Friday at 10 pm, and all 25 are deployed together because versions must match. Checkout latency is 1.8 s, since one request passes through 7 services in a row. The `orders` table is read directly by four other services, so a column rename needs four teams to coordinate. One night the loyalty service slows down, threads pile up in checkout, and the whole site returns errors for 20 minutes. The team has the cost of microservices and the rigidity of a monolith.

**What the interviewer is really checking**
Whether you can spot coupling in architecture, not only in code. They also want to know whether you can explain the fix in terms of boundaries and data ownership, not just "add Kafka".

**How I answer it**
1. **Lockstep deployment.** If services must be released together, they are not independent. The cause is usually breaking API changes or shared contracts, so check whether one service can ship alone.
2. **Shared database.** If several services read or write the same tables, the schema becomes a hidden API. Any change risks breaking someone. The fix is one owner per table, with others using its API or events.
3. **Long synchronous chains.** Each hop adds latency and failure probability. For example, 7 services at 99.9% availability each give roughly 99.3% combined. Replace non-essential calls with events, or keep needed data locally.
4. **Big shared library with domain logic.** A change to it forces every service to upgrade and redeploy, so it acts as a monolith in disguise. Keep shared libraries to technical utilities (logging, auth helpers). Let each service own its domain rules.
5. **One failure takes everything down.** This means there are no timeouts, circuit breakers or fallbacks, and the failure cascades. Add those, and make the call asynchronous where the business allows.
6. **Remedy.** Re-draw boundaries around business contexts, introduce events, remove the shared database and shrink shared libraries. Do it incrementally and start where the pain is greatest.

Other symptoms:
- A single feature needs changes in many services and teams.
- Testing needs the whole system running.
- Services are chatty, with many tiny calls per request.

**Trade-offs and what can go wrong**
- Events alone do not fix a bad boundary. If services still need each other's data immediately, you get hidden coupling plus eventual consistency.
- Removing a shared database means giving up cross-service joins and transactions. You then need sagas, the outbox pattern and idempotent consumers.
- Sometimes merging services back together is the right answer. Too-fine boundaries cause most distributed monoliths.
- Duplicating a little code is often cheaper than coupling services through a shared library.

**How I'd monitor it**
- Deployment metrics: how many services ship in each release, and lead time per service.
- Distributed tracing (for example OpenTelemetry): trace depth and the number of synchronous hops per request.
- Dependency graph and database access audit: which services touch which tables.
- Per-service p99 latency and error rate. Alert when one service's errors spread to its callers.
- Splunk: search by correlation id to see whether one incident touches many services.
- Circuit breaker open counts and thread pool saturation.

**Follow-ups to expect**
- *Is a synchronous call always bad?* -> No. Use it when the caller needs the answer now, with timeouts, retries and circuit breakers. Avoid long chains.
- *How do you break up a shared database safely?* -> Assign each table an owner, route other readers through the owner's API or events, then split the schema. Use the outbox pattern to publish changes reliably.
- *Would you go back to a monolith?* -> If the team is small and the boundaries are unclear, a modular monolith is often better. Split later along proven boundaries.

**60-second answer**
A distributed monolith is a system split into services that still behave like one application. The signs are that services must be deployed together, that they share a database, and that requests pass through long synchronous call chains. Another sign is a large shared library with domain logic, and a third is that one slow service takes everything down. All of these mean teams cannot change or release independently. The fix starts with business boundaries: one service owns its data, and others use its API or events. I replace non-essential synchronous calls with events, add timeouts and circuit breakers, and keep shared libraries to technical utilities. I would measure progress by how many services ship alone and how many hops a request makes in traces.

### Q16 [architect] Design for high availability: what do you do at service, data and infrastructure level?
tags: high-availability, microservices, kubernetes, resilience, failover, rto-rpo, basics

**Start here: the concepts**
- **High availability (HA):** the system keeps serving users when a part of it fails. It works by removing single points of failure through redundancy.
- **Replica:** an identical running copy of a service. If one dies, the others keep serving.
- **Availability zone (AZ):** an isolated data-centre location within a cloud region. Zones fail independently, so spreading across them survives a zone outage.
- **Readiness vs liveness probe:** readiness asks "can you take traffic now?" and a failing pod is removed from load balancing. Liveness asks "are you stuck?" and a failing pod is restarted.
- **Graceful shutdown:** on a stop signal the service stops accepting new requests, finishes in-flight ones, then exits. Without it, every deploy or scale-down drops requests.
- **Timeout and circuit breaker:** a timeout stops waiting on a slow dependency. A breaker stops calling a failing dependency for a while, so one bad service does not exhaust everyone's threads.
- **Idempotent write:** doing it twice has the same effect as doing it once. This makes retries after a failover safe.
- **Failover:** automatically promoting a standby (replica) database to primary when the primary fails.
- **Pod anti-affinity / topology spread:** Kubernetes rules that stop replicas landing on the same node or zone.
- **PodDisruptionBudget (PDB):** a rule such as "never take down more than 1 pod at once" during planned maintenance.
- **Single point of failure (SPOF):** any one component whose failure takes everything down.
- **RTO / RPO:** Recovery Time Objective is how long you can be down. Recovery Point Objective is how much data you can afford to lose, measured in time.

**The live scenario**
An order service ran 3 replicas, so the team felt safe. The scheduler had put all 3 on nodes in one zone. That zone lost networking for 12 minutes and checkout was fully down at about 2,000 orders/min. Later they found that the database replica was also in that zone, and nobody had ever rehearsed a failover. Having "3 replicas" was not high availability, because they were not independent.

**What the interviewer is really checking**
Whether you think in failure domains (pod, node, zone, dependency) rather than just "more copies". Also whether you tie the design to business targets (RTO/RPO) and prove it by testing.

**How I answer it**
1. **Set RTO and RPO first.** They decide how much redundancy is worth paying for. Zero data loss needs synchronous replication, which costs latency.
2. **Service level.** Run at least 3 replicas spread across zones, so losing one still leaves capacity. Use readiness probes so traffic only reaches healthy pods, and liveness probes only for real deadlocks. Add graceful shutdown so deploys do not drop requests. Put timeouts on every outbound call and add circuit breakers, so a slow dependency does not turn into a full outage.
3. **Data level.** Use a replicated database with automatic failover. Take backups and restore them regularly, because an untested backup is only a hope. Make writes idempotent so client retries during failover do not create duplicates.
4. **Infrastructure level.** Use multi-AZ node pools and force the spread, for example:
   ```yaml
   topologySpreadConstraints:
   - maxSkew: 1
     topologyKey: topology.kubernetes.io/zone
     whenUnsatisfiable: DoNotSchedule
   ```
   Add PodDisruptionBudgets so maintenance cannot remove too many pods, and autoscaling to absorb load when capacity drops. Remove SPOFs in the gateway, DNS and queue by making each redundant too.
5. **Test it.** Kill a pod, a node and a zone on a schedule (game days), and rehearse database failover. Compare the measured recovery with the RTO and RPO.

**Trade-offs and what can go wrong**
- Redundancy costs money, and cross-zone traffic adds latency and fees.
- Asynchronous replication is fast but can lose recent writes at failover, so RPO is above zero.
- Backups protect against corruption and deletion, which replication copies faithfully. They are recovery, not availability.
- A badly tuned liveness probe can restart healthy but slow pods, causing a restart storm.
- Autoscaling does not help if a shared dependency is the bottleneck.
- A multi-AZ design does not survive a whole-region outage. That needs multi-region, which costs far more and brings consistency problems.

**How I'd monitor it**
- Availability SLO and error-budget burn alerts.
- Pods ready per zone, and alerts when any zone drops below the minimum.
- Replication lag against the RPO.
- Failover duration from drills.
- Circuit-breaker open counts and timeout rates.
- Last successful restore test date.
- Splunk searches for error spikes grouped by zone.

**Follow-ups to expect**
- *Is HA the same as disaster recovery?* -> No. HA handles routine component or zone failures with little or no downtime. DR recovers from a large loss, such as a region or data corruption, using backups or another region, usually with some downtime.
- *Sync or async database replication?* -> Sync gives RPO near zero but adds write latency and can block when the standby is down. Async is faster but can lose recent writes. Choose based on the RPO.
- *Why a PDB if you already have replicas?* -> Replicas protect against failures. A PDB protects against voluntary actions such as node drains and upgrades, which could otherwise remove all replicas together.

**60-second answer**
I start from the business targets, RTO and RPO, because they set how much redundancy is worth it. At service level I run several replicas across zones, with readiness and liveness probes, graceful shutdown, timeouts and circuit breakers. At data level I use a replicated database with automatic failover, backups I actually restore-test, and idempotent writes so retries are safe. At infrastructure level I use multi-AZ nodes, topology spread and anti-affinity, PodDisruptionBudgets and autoscaling. I also make sure the gateway, DNS and queue are not single points of failure. The cost is money, latency and eventual-consistency risk, and only regular failover drills prove the design works. I would watch per-zone readiness, replication lag and failover time.

### Q17 [architect] Design the observability for 30 microservices.
tags: microservices, observability, opentelemetry, metrics, distributed-tracing, slo, basics

**Start here: the concepts**
- **Observability:** the ability to work out what is going wrong inside a system from the data it emits, without shipping new code. With 30 services a request crosses many processes, so you cannot debug by reading one server's log.
- **Metrics:** numbers sampled over time, such as requests per second. They are cheap and good for alerting and trends, but they don't tell you which single request failed.
- **RED:** the three metrics to track per endpoint. **R**ate is requests per second, **E**rrors is the failing share, **D**uration is how long requests take (use percentiles like p99, not averages).
- **Golden signals:** Google SRE's four: latency, traffic, errors, saturation. RED covers the first three. Saturation (how full a resource is) comes from JVM and pool metrics such as heap, GC pauses, thread pools and DB connection pools.
- **Logs:** timestamped event records. **Structured JSON** logs have named fields (`service`, `level`, `traceId`), so a central store like Splunk can filter them reliably instead of using text patterns.
- **Trace / span:** a trace is the journey of one request across services. Each hop is a **span** with a start time and duration. **OpenTelemetry (OTel)** is the vendor-neutral standard for producing traces, metrics and logs.
- **Correlation id (`traceId`):** one id passed along every hop (HTTP header, Kafka message header) so metrics, logs and traces about the same request can be joined.
- **SLO:** a target such as "99.9% of checkout requests succeed over 30 days". The **error budget** is the allowed 0.1% of failures. **Burn rate** is how fast you spend that budget; burn rate 1 uses it up exactly at the end of the window.
- **Runbook:** a short document that says what an alert means and what to check and do first.

**The live scenario**
Checkout handles about 2,000 requests/s across 30 services. One evening p99 latency rises from 400 ms to 6 s. Each team's dashboard looks "fine", and it takes 45 minutes of searching logs service by service to find the cause. The inventory service had exhausted its DB connection pool after a slow query. Customers abandoned carts the whole time. With the design below, a burn-rate alert fires within minutes, and one trace shows the time spent waiting for a connection inside inventory.

**What the interviewer is really checking**
Whether you treat observability as a platform with standards (one correlation id, shared conventions, alerts tied to user impact) rather than a pile of tools. They also want to see that you can cover async hops like Kafka and keep the cost under control.

**How I answer it**
1. **Set one standard for all 30 services.** Use a shared starter library or OTel agent with common naming and mandatory fields. Without it each team invents its own format and cross-service search fails.
2. **Metrics:** RED per endpoint plus JVM and pool metrics. RED shows the user's pain, and pool and JVM metrics show saturation, the usual cause.
3. **Logs:** structured JSON that always carries `traceId` and `service`, shipped to central search (e.g. Splunk). A search such as `index=prod traceId=abc123` then returns that request's story across all services.
4. **Traces:** OTel propagates the trace context over HTTP headers. Kafka has no request/response, so the producer puts the context in message headers and the consumer continues from it. Otherwise the trace breaks at every topic.
5. **Alert on SLOs, not on every CPU spike.** Burn-rate alerts (fast burn pages someone, slow burn opens a ticket) fire when users are affected. Use the golden-signal dashboard for diagnosis.
6. **Attach a runbook to every alert**, so a tired on-call engineer knows the first three checks.

**Trade-offs and what can go wrong**
- **Cost:** tracing every request at 2,000 req/s is expensive, so sample. Keep all error and slow traces if your tooling allows it.
- **High-cardinality labels** (user id, order id) as metric labels can blow up the metrics store. Put them in logs or traces instead.
- **Alert fatigue:** too many alerts get ignored. Page only on user impact.
- **Broken propagation:** one service that drops the header splits the trace in two. Test it.
- **Sensitive data:** keep PII and secrets out of logs.

**How I'd monitor it**
Monitor the observability itself: the share of requests with a `traceId` in logs, the share of Kafka consumers that continue a trace, log ingestion lag, dropped spans, and the number of alerts that have a runbook. Review alert noise after each incident.

**Follow-ups to expect**
- *Metrics, logs or traces: which first?* -> Metrics and SLO alerts tell you something is wrong, traces tell you where, and logs tell you why.
- *How do you trace through Kafka?* -> Inject the trace context into message headers on produce and extract it on consume. For batches, use span links.
- *Why burn-rate alerts instead of a threshold?* -> They measure how fast the error budget is being spent, so they page on real user impact and ignore brief blips.

**60-second answer**
I'd build observability as a shared platform with one correlation id. Every service emits RED metrics per endpoint plus JVM and connection-pool metrics, writes structured JSON logs containing `traceId` to central search such as Splunk, and sends OpenTelemetry traces. The trace context travels in HTTP headers and Kafka message headers so async hops stay connected. On top of that I define SLOs per service and alert on error-budget burn rate, so we page on user impact and not on noise. Golden-signal dashboards help diagnose, and every alert links to a runbook. I'd watch the costs: sampling traces, avoiding high-cardinality metric labels, and keeping alerts few enough to be trusted.

### Q18 [mid] When should you NOT use microservices?
tags: microservices, modular-monolith, bounded-context, architecture, distributed-systems, devops, basics

**Start here: the concepts**
- **Monolith:** one application, built and deployed as one unit. Calls between its parts are ordinary method calls, which are fast and can share one database transaction.
- **Microservice:** a small service that owns one business capability and its own data, and is deployed on its own. Services talk over the network (REST or messaging). It exists so that many teams can change and release parts of a system independently.
- **Bounded context:** a part of the business with its own vocabulary and rules, such as "Billing" or "Shipping". Good service boundaries follow these contexts.
- **Modular monolith:** one deployable application split inside into modules with clear public interfaces. Modules do not reach into each other's code or tables.
- **Eventual consistency:** when data lives in separate services, you cannot update it all in one transaction. The copies agree after a short delay, and you must design for the gap.
- **DevOps maturity:** the team can automate builds, deployments, monitoring and on-call. Many services means many pipelines and many things to watch.
- **Correlation id and tracing:** an id attached to a request as it passes through services, so you can follow it end to end. Without it, debugging across services is guesswork.

**The live scenario**
A 6-person startup is building an order-management app. Management wants "Netflix-style" microservices, so they build 12 services. Each service needs its own pipeline, database and alerts. Releases slow from daily to weekly because a single feature touches 3 services and needs coordinated deploys. In month 4 they learn that "Customer" and "Account" were really one concept, and merging the services and their databases takes six weeks. Traffic is about 50 requests per second, which one small server could handle.

**What the interviewer is really checking**
Whether you treat microservices as a tool with costs, not a default. They want to see that you can name the conditions that justify the cost and propose a sensible alternative.

**How I answer it**
1. **Small team: avoid microservices.** Each service adds code, pipelines and on-call work. A small team spends its time on plumbing instead of features.
2. **Unclear domain: avoid them.** If you don't yet know where the business boundaries are, you will draw them wrong. Moving a boundary inside a monolith is a refactor. Across services it means changing APIs, data stores and deployments.
3. **Simple CRUD: avoid them.** CRUD means create, read, update and delete on records. There is little business logic to separate, so the network calls add cost and no benefit.
4. **Low scale: be careful.** Scaling parts independently is one benefit of microservices, so with low load you don't need it. But scale is not the only reason to adopt them. Independent deployment and team autonomy matter too, and a small, low-traffic system rarely needs those either.
5. **No DevOps maturity: avoid them.** Without automated deployment, monitoring and tracing, a distributed system is hard to run and hard to debug.
6. **Start with a modular monolith.** It is faster to build, you keep simple local transactions, and it is easier to test and debug. Splitting later is easy only if you enforce the boundaries: modules talk through interfaces, and each module owns its own tables. Split out a module when a real need appears, such as a different scaling profile or a separate team.

**Trade-offs and what can go wrong**
- A monolith without enforced boundaries becomes a "big ball of mud", and then splitting it later is hard. The modular discipline matters.
- One deployable means one release cadence and a shared failure domain, so a bug in one module can take everything down. That is a real limit once many teams work in it.
- Microservices bring network failures, latency, eventual consistency, versioned APIs and harder debugging. Teams that adopt them too early often build a "distributed monolith": services that still must be deployed together, with all the costs and none of the benefits.

**How I'd monitor it**
- For the monolith, check module boundaries automatically in the build, for example with ArchUnit tests that fail on forbidden dependencies.
- Track deploy frequency, lead time from commit to production, and build time. If these slow down and teams block each other, that is the signal to split.
- If you do run services, search Splunk by correlation id to follow one request across them. Also watch inter-service latency and error rates, and look for services that always deploy together.

**Follow-ups to expect**
- *How do you know it's time to split?* -> When teams block each other's releases, one part needs very different scaling, or a stable boundary has been clear for a while.
- *What is a distributed monolith?* -> Services that are tightly coupled and must be changed or deployed together, so you pay the network cost without independence.
- *Is a modular monolith just a messy monolith?* -> No. It has enforced module boundaries and no cross-module table access, which is what makes later splitting cheap.

**60-second answer**
I would avoid microservices when the team is small, the domain is unclear, the app is mostly simple CRUD, the scale is low, or the team lacks DevOps maturity. Microservices cost more in pipelines, monitoring, network failures and eventual consistency, so they only pay off when many teams need to deploy and scale independently. If the domain is unclear, I'd draw the boundaries wrong, and fixing that across services is very expensive. I'd start with a modular monolith with clear modules, interfaces and separate data ownership per module. That is faster to build and debug, and it can be split later when there is a real need. I'd enforce the boundaries with automated checks so the split stays easy.

### Q19 [mid] What is CQRS and when is Event Sourcing worth it?
tags: cqrs, event-sourcing, microservices, eventual-consistency, projections, kafka, basics

**Start here: the concepts**
- **Write model:** the part of the code that accepts changes (commands such as "place order") and enforces business rules. It is tuned for correctness.
- **Read model:** a copy of the data shaped for the screens or APIs that query it, for example a flat "order summary" table. It is tuned for fast reads and is often a separate store.
- **CQRS (Command Query Responsibility Segregation):** using separate models for changing data and for reading it. It exists because one model rarely suits both jobs: complex joins slow down reads, while read-friendly shapes make rule enforcement awkward.
- **Event:** an immutable fact that already happened, such as "OrderPlaced" or "PaymentRefunded".
- **Event sourcing:** saving the list of events as the source of truth (append-only, never updated or deleted) instead of saving the current state. To get the current state, you replay the events.
- **Projection:** code that consumes events and builds or updates a read model.
- **Snapshot:** a saved state at some point, so replay starts from there instead of from event one.
- **Eventual consistency:** a read model may lag the write side by a short time, then catches up.
- **Schema evolution:** events are stored forever, so old event formats must still be readable after the code changes.

CQRS and event sourcing are independent. You can use CQRS with a normal database, and that is the common, cheaper choice.

**The live scenario**
An order-history screen joins six tables and takes 1.2 s at peak (about 800 reads/s against 40 writes/s). Reads are slowing down writes on the same database. The team adds a denormalised read store fed by order events, and the screen drops to about 30 ms. That is CQRS, and it needs no event sourcing. Separately, the finance team must explain exactly how an account balance reached its value on any past date. Only there does the team store every movement as an event, and it accepts the extra cost because audit and replay are the core requirement.

**What the interviewer is really checking**
That you know CQRS and event sourcing are separate ideas, and that you can say when the extra complexity pays off, not just recite definitions.

**How I answer it**
1. **Define CQRS simply.** Separate write model from read models. The reason is that reads and writes have different needs and scale differently.
2. **Say the read side is usually a separate store, updated asynchronously.** This makes reads fast and independently scalable, but it creates eventual consistency, which comes from the separate store, not from event sourcing.
3. **Define event sourcing.** State is an append-only list of events, and current state is rebuilt by replaying them. This gives a complete audit trail, the ability to replay history, and the ability to build new read models from old events.
4. **Name the costs.** Event schemas must evolve safely, long event streams need snapshots, and the team needs to learn a different way of working.
5. **Give the rule.** Use CQRS when read and write needs clearly differ. Use event sourcing only where history is a core requirement, such as finance or a ledger. For most CRUD services, neither is needed.

**Trade-offs and what can go wrong**
- Users may not see their own write immediately. Mitigate with read-your-writes tricks, such as returning the new state from the command response.
- Events are permanent, so a badly designed event is hard to fix. Version events and convert old versions when reading.
- Replaying millions of events is slow without snapshots.
- Projections can fail or fall behind. They must be idempotent (safe to process the same event twice) and rebuildable.
- Common mistake: adopting event sourcing "because it's modern" for simple data. Another is treating a message log, such as a Kafka topic, as a full event store without thinking about retention and ordering.

**How I'd monitor it**
- Projection lag, meaning the time or number of events between write and read model. If projections run via Kafka, watch consumer lag.
- Event append latency and error rate.
- Replay or rebuild duration, and snapshot age.
- Dead-letter queue (DLQ) count for events that failed projection.
- In Splunk, search by correlation id to follow a command through its events to the projection.
- Alert when lag exceeds the agreed staleness limit, for example 5 s.

**Follow-ups to expect**
- *Do you need event sourcing for CQRS?* -> No. CQRS only needs separate read and write models, and event sourcing is an optional way to store the write side.
- *How do you handle a user not seeing their change right away?* -> Return the updated data from the command, or read from the write side briefly, and tell users updates may take a moment.
- *How do you change an event's format later?* -> Version events and convert old versions when reading them (upcasting). Never rewrite stored history.

**60-second answer**
CQRS means I use one model to handle changes and separate read models for queries, often in a different store, because reads and writes have different needs. The price is eventual consistency, since the read side updates a moment later. Event sourcing is a different idea: instead of storing current state, I store an append-only list of events and replay them to rebuild state. That gives a full audit trail and replay, but brings schema evolution, snapshots and a learning curve. So I use CQRS when read and write needs really differ, and event sourcing only where history is a core requirement, like a finance ledger. I would watch projection lag and replay time to keep it healthy.

### Q20 [mid] How should services communicate?
tags: microservices, synchronous, asynchronous, rest, grpc, kafka, basics

**Start here: the concepts**
- **Service-to-service communication:** In a microservice system, each service is a separate program. They cannot call each other's methods directly, so they must send messages over the network.
- **Synchronous communication:** The caller sends a request and waits for the answer before continuing. HTTP/REST (JSON over HTTP) and gRPC (a faster, strictly typed binary protocol over HTTP/2) are the usual choices. Use it when the caller cannot proceed without the result.
- **Asynchronous communication:** The sender puts a message on a broker such as Kafka and moves on. The receiver processes it later. It exists so the two sides do not have to be up, or equally fast, at the same moment.
- **Message broker:** Middleware that stores messages between sender and receiver. Kafka is one example.
- **Coupling:** How much one service must know about, or depend on, another. Tight coupling means one service's failure or change breaks the other.
- **Buffering:** The broker absorbs a burst of messages so a slower consumer can catch up at its own pace.
- **Event-driven workflow:** Services publish facts ("OrderPlaced") and other services react on their own, instead of being told what to do.
- **Ordering:** Messages being processed in the sequence they were sent. Kafka guarantees this only within one partition, so messages that must stay in order need the same key.
- **Consistency:** Whether all services see the same data at the same time. Async usually gives eventual consistency, meaning data agrees after a short delay.

**The live scenario**
An e-commerce checkout calls payment, inventory, shipping and email services one after another over REST. At 2,000 orders/minute it works. During a sale, the email service slows to 8 seconds per call. Checkout threads pile up waiting, and checkout latency goes from 300 ms to 10+ seconds. Orders fail even though email is not essential. The team keeps payment and inventory synchronous, because the customer needs the answer now. They publish "OrderPlaced" to Kafka for email and shipping. Checkout stays at about 400 ms, and email catches up after the peak.

**What the interviewer is really checking**
Whether you pick sync or async from the requirement (latency, failure impact, consistency) rather than by fashion. They also want to see that you know async brings costs of its own.

**How I answer it**
1. **Ask whether the caller needs the answer to continue.** If yes (a price lookup, a payment authorisation), use synchronous REST or gRPC, because the caller cannot proceed without it. A simple request/response is easier to reason about and debug.
2. **If the work can happen later, or many services react to one fact, use async.** Examples are notifications, analytics and shipping. The sender does not wait, so a slow or down consumer does not hurt it.
3. **Use async to buffer bursts and decouple.** The broker holds the backlog, so consumers can scale or restart without losing work.
4. **Do not use async just to avoid designing a proper API.** If you need an answer, hiding a request/response behind two topics only adds delay and complexity.
5. **Decide using these factors:** latency, coupling, failure handling, throughput, ordering and consistency.
6. **Protect sync calls** with timeouts, limited retries and circuit breakers, so a slow dependency fails fast instead of exhausting threads.
7. **Make async consumers idempotent** (safe to process the same message twice), because brokers can deliver duplicates. Publish events reliably, for example with a transactional outbox.

**Trade-offs and what can go wrong**
- **Sync:** Long call chains multiply failure chances. If each of 4 services is 99.9% available, the chain is lower. It also creates temporal coupling, meaning both sides must be up at the same time.
- **Async:** You get eventual consistency, duplicates, possible reordering across partitions, and harder debugging. Event schemas also couple services, since changing a message format can break consumers.
- **Common mistakes:** Using sync for everything, using Kafka for every call, and forgetting correlation IDs so you cannot trace a request across services.

**How I'd monitor it**
- **Sync calls:** p95/p99 latency, error rate, timeouts and circuit breaker state per dependency.
- **Async:** Consumer lag per group, message age, dead-letter queue size and redelivery counts.
- **Tracing:** A correlation/trace ID in every request and message header. Search for it in Splunk to follow one order across services.
- **Alerts:** Rising lag or latency, and open circuit breakers.

**Follow-ups to expect**
- *How do you avoid cascading failures with sync calls?* -> Timeouts, bounded retries with backoff, circuit breakers, bulkheads and fallbacks.
- *REST or gRPC?* -> REST is simple and widely supported. gRPC is faster and strictly typed, which suits internal, high-volume calls.
- *How do you handle duplicate messages?* -> Make consumers idempotent, for example by storing processed message IDs or using upserts.

**60-second answer**
I choose based on whether the caller needs the answer right now. If it does, such as for payment authorisation, I use synchronous REST or gRPC with timeouts and circuit breakers. If the work can happen later, or several services react to the same event, I use asynchronous messaging like Kafka. It gives buffering and decoupling, so a slow consumer does not slow the producer. I never use async just to dodge designing a clear API. Async costs eventual consistency, duplicates, and ordering only per partition, so consumers must be idempotent. I decide using latency, coupling, failure handling, throughput, ordering and consistency, and I monitor latency, consumer lag and trace IDs.

### Q21 [mid] What is service discovery?
tags: service-discovery, microservices, kubernetes, dns, load-balancing, resilience, basics

**Start here: the concepts**
- **Service instance:** one running copy of a service. To handle more traffic, you run several copies of the same service.
- **Why hardcoded addresses break:** an instance's IP address and port change whenever it restarts, scales up or moves to another machine. A fixed address in a config file soon points at nothing.
- **Service discovery:** a way for a caller to find the current, healthy instances of a service by name (for example `orders`) instead of by address. It exists because instances constantly come and go.
- **Health check:** a small probe, such as an HTTP `/health` call, that tells the platform whether an instance can take traffic. Discovery should only hand out healthy instances.
- **Service registry:** a dedicated database of "service name -> live instances". Instances register themselves, or the platform does it for them. Eureka and Consul are examples.
- **Kubernetes Service and DNS:** Kubernetes gives each Service a stable name and virtual address. Its DNS resolves the name, and the platform routes traffic only to ready pods.
- **Platform load balancer:** a component that spreads requests across instances. It can do discovery and balancing for you.

**The live scenario**
A checkout service calls the payment service at a fixed IP from a config file. During a Friday sale, traffic goes from 200 to 1,500 requests per second. Autoscaling adds 6 payment instances and replaces 2 crashed ones. The checkout service still sends everything to the 3 original addresses. Two of them are dead, so roughly 60% of payments fail with "connection refused" for 15 minutes until someone edits the config. The fix is to call the payment service by name and let the platform track which instances are alive.

**What the interviewer is really checking**
Whether you understand the problem (instances are dynamic) and the options (platform-provided or registry-based). Also whether you avoid adding infrastructure you don't need.

**How I answer it**
1. **Define the problem first.** Instances change address all the time, so callers must look them up by name at call time. Otherwise every restart or scale event becomes a config change and an outage risk.
2. **Name the three common sources.** Kubernetes DNS/Services, a platform load balancer, or a dedicated registry. Each one keeps a live list of instances.
3. **Say how healthy instances are chosen.** Instances that fail health or readiness checks are removed from the list, so callers don't get sent to broken copies.
4. **Pick the simplest option for the platform.** On Kubernetes, the caller just uses the service name:
   ```
   http://payment-service/api/payments
   ```
   DNS and platform routing do the rest, so no extra library or server is needed.
5. **Add a dedicated registry only for a concrete need.** For example, services running across VMs and containers with no common platform, or custom routing rules the platform can't express. Each extra system is one more thing to run, secure and debug.

**Trade-offs and what can go wrong**
- **Two styles:** server-side discovery (the platform or load balancer picks the instance) is simple for callers. Client-side discovery (the caller fetches the list and picks) gives more control but puts logic in every service.
- **Stale data:** caches, including the JVM's DNS cache, can keep returning dead instances for a while.
- **Wrong health checks:** a probe that always says "OK" sends traffic to broken instances. One that is too strict removes everything at once.
- **Registry as a dependency:** if a dedicated registry goes down, callers may not find anyone, so it needs high availability.
- **Not a resilience tool:** discovery finds instances but doesn't handle slow or failing ones. You still need timeouts, retries and circuit breakers.

**How I'd monitor it**
- Number of ready endpoints per service, with an alert when it drops below the expected minimum.
- Readiness probe failures and pod restarts.
- Error rate for connection refused, timeouts and unknown-host errors, by target service. In Splunk, search those exception messages grouped by the called service.
- DNS lookup latency and failures.
- Tracing with correlation ids, to see which instance served a failed call.

**Follow-ups to expect**
- *Client-side vs server-side discovery?* -> Client-side: the caller queries a registry and chooses an instance. Server-side: the caller hits a stable name or load balancer that chooses. Kubernetes Services are server-side.
- *Do I need Eureka on Kubernetes?* -> Usually not. Kubernetes already provides naming, health-based routing and load balancing. I'd add a registry only for a specific need it can't meet.
- *What if a dead instance is still being called?* -> Check the readiness probe and DNS caching. Add short timeouts, limited retries and a circuit breaker so callers recover quickly.

**60-second answer**
Service discovery lets services find healthy instances of other services by name instead of hardcoded addresses, because instances restart, scale and move all the time. It can be provided by Kubernetes DNS and Services, a platform load balancer, or a dedicated registry. Health checks keep broken instances out of the list. On a container platform, service names and platform routing are usually enough, so I wouldn't add a separate discovery system without a concrete need. The risks are stale caches and poor health checks, so I'd monitor ready endpoint counts and connection errors per service. Discovery also doesn't replace timeouts and circuit breakers.
