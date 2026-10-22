---
id: company-chase-travel-domain
title: Company pack, Chase Travel (2/2): rewards travel platform design (10 questions)
stack: java
skill: architecture
---
Company-level pack for a **Chase Travel / Java rewrite** engagement (see `../company-chase-travel/README.md`).

**Illustrative, not insider knowledge.** These are system-design scenarios for a **card-rewards travel booking platform**
(search, price in points and cash, book with suppliers, service the trip), built from public facts and common
travel-industry practice: GDS and NDC airline content, hotel aggregators, PCI DSS, loyalty ledgers. Use them to show
domain fluency, and in the room phrase them as "in a platform like yours...".

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [architect] Design the high-level architecture of a card-rewards travel booking platform.
tags: system-design, travel-platform, microservices, loyalty, architecture, booking, company-chase-travel

**Start here: the concepts**
- **Travel content sources:** GDS (global distribution systems such as Amadeus, Sabre, Travelport), airline NDC APIs (IATA's New Distribution Capability), hotel and car aggregators/suppliers.
- **Rewards travel:** customers pay with **points**, cash (card), or both; points come from a loyalty ledger owned by the card programme.
- **Look-to-book ratio:** searches per booking, often in the hundreds or thousands, so search load dwarfs booking load.

**The live scenario (functional requirement)**
*FR: "Card members search flights, hotels, cars and activities, see prices in points and cash, book with points, card or a mix, get confirmations, and manage changes and cancellations, on web and mobile, with customer-service agents supporting them."*

**What the interviewer is really checking**
A coherent decomposition with the right data flows, consistency points and scaling hot spots.

**How I answer it**
1. **Edge:** CDN, WAF, API gateway; BFFs for web/mobile; agent desktop for servicing.
2. **Search & content (read-heavy, cached):** search service fans out to supplier adapters (GDS/NDC/hotel APIs), merges and ranks; static content (hotel descriptions, images) in a content service with CDN; availability cache with short TTLs.
3. **Pricing:** converts supplier prices into member prices: markups, taxes, **points conversion by member tier/promotions**; produces a signed **quote** with TTL.
4. **Booking orchestration:** saga across points hold, card payment, supplier booking, ticketing; state machine per booking.
5. **Payments & points:** payment service (tokenised cards, PCI scope isolated) and a **points ledger** integration (hold/debit/refund).
6. **Fulfilment & servicing:** ticketing, vouchers, confirmations, changes/cancellations, refunds, supplier schedule changes (airline schedule-change feeds).
7. **Events backbone (Kafka):** booking events feed notifications, trip history (CQRS read model), analytics, fraud, and the AI assistant's context.
8. **Cross-cutting:** identity (card member SSO), observability, feature flags, config, secrets; multi-AZ Kubernetes; DR for booking-critical paths.

**Trade-offs and what can go wrong**
- Search load can overwhelm suppliers (and cost per call); caching and rate limits are central.
- Prices change between search and book; quotes and re-validation are needed (Q5).
- Booking is a distributed transaction across systems you don't control; sagas and reconciliation are essential.

**How I'd monitor it**
Business KPIs: searches, look-to-book, booking success rate per supplier, payment failures, points holds outstanding; technical: latency per service and supplier, error budgets.

**Follow-ups to expect**
- *Where's the source of truth for a booking?* -> The booking service (our record) plus the supplier's PNR/reservation; reconcile both.
- *What's a PNR?* -> Passenger Name Record, the airline/GDS reservation record.
- *Hardest part?* -> Consistency with external suppliers and peak search load.

**60-second answer**
"Behind the edge and BFFs, a read-heavy search tier fans out to GDS, NDC and hotel supplier adapters with aggressive caching, because look-to-book ratios are huge. A pricing service turns supplier prices into member prices in points and cash and issues a signed quote with a TTL. Booking orchestration is a saga across points hold, tokenised card payment and the supplier reservation, with a state machine per booking. Fulfilment and servicing handle tickets, changes and refunds, and Kafka booking events feed notifications, trip history, fraud, analytics and the AI assistant."

### Q2 [senior] Aggregate hotel and flight search across many suppliers within a latency budget.
tags: search-aggregation, caching, fan-out, latency-budget, suppliers, look-to-book, company-chase-travel

**Start here: the concepts**
- **Fan-out/fan-in:** call suppliers in parallel, merge, de-duplicate (same hotel from two suppliers), rank.
- **Availability caching:** prices and availability change often; cache with short TTLs and refresh asynchronously.
- **Supplier constraints:** rate limits, per-call costs, look-to-book agreements.

**The live scenario (functional requirement)**
*FR: "Hotel search for a city and dates returns results from 5 suppliers in under 2 s p95, showing the best member price per property; supplier API costs must stay within budget."*

**What the interviewer is really checking**
Practical aggregation engineering: parallelism, timeouts, caching, de-duplication, cost.

**How I answer it**
1. **Cache-first:** check an availability cache keyed by (supplier, city, dates, occupancy) with a TTL of minutes; serve cached results immediately and refresh in the background for popular searches.
2. **Parallel fan-out** for misses: each supplier adapter with a timeout (1.5 s), bulkhead and circuit breaker; virtual threads or async clients.
3. **Progressive results:** return what's ready by the deadline; optionally stream more results to the UI (SSE) as late suppliers respond.
4. **Mapping & de-duplication:** a property-mapping service maps supplier hotel ids to our master property id; keep the best price per property, with supplier choice also considering margin and reliability.
5. **Ranking:** price, relevance, member preferences, conversion history.
6. **Cost control:** respect supplier rate limits and look-to-book quotas; cache aggressively; pre-fetch popular destinations off-peak.
7. **Detail/re-price step:** when a user selects a property, fetch live rates for accuracy (Q5).

**Trade-offs and what can go wrong**
- Stale cached prices cause price-change errors at booking; balance freshness vs cost.
- Waiting for the slowest supplier ruins latency; partial results are better.
- Mapping errors show duplicates or wrong properties; mapping needs ongoing curation.

**How I'd monitor it**
p95 search latency, per-supplier latency/timeouts/breaker state, cache hit ratio, supplier call volume vs quota, price-change rate at booking.

**Follow-ups to expect**
- *How do you choose TTLs?* -> From price volatility data per supplier and destination, and cost per call.
- *Search for flights differs how?* -> Fare complexity and GDS/NDC costs are higher; caching shopping results is common, with re-pricing before booking.
- *Personalisation?* -> Ranking features from member history, kept privacy-safe.

**60-second answer**
"Cache first: availability cached per supplier, city, dates and occupancy for a few minutes, refreshed in the background for popular searches. Misses fan out in parallel to supplier adapters, each with a timeout, bulkhead and circuit breaker, and I return what's ready by the deadline, streaming late results if the UI supports it. A mapping service de-duplicates properties across suppliers to show the best member price. Supplier rate limits and look-to-book quotas drive caching, and the selected property is re-priced live before booking."

### Q3 [senior] Pay with points, card, or both: keep the points ledger and payment consistent.
tags: split-payment, points-ledger, saga, payments, consistency, idempotency, company-chase-travel

**Start here: the concepts**
- **Points ledger:** append-only entries (earn, redeem, hold, release, refund); balance derived.
- **Hold (authorisation) then capture:** for both points and card, reserve first, capture after the supplier confirms.
- **Saga with compensations** across ledger, payment processor and supplier.

**The live scenario (functional requirement)**
*FR: "A member books a $900 hotel paying 50,000 points and $400 on their card; if the hotel booking fails, points return immediately and the card isn't charged; no double-spend of points across devices."*

**What the interviewer is really checking**
Correct ordering, idempotency and concurrency control in money-like flows.

**How I answer it**
1. **Quote** fixes the split (points amount, cash amount) with a TTL.
2. **Points hold:** ledger creates a HOLD entry for 50,000 points with an idempotency key (booking id); balance check and hold are atomic (row lock or optimistic version on the member account), preventing double-spend from two devices.
3. **Card authorisation** for $400 via the payment service (tokenised card), idempotency key = booking id.
4. **Supplier booking** with its own idempotency/reference.
5. **Success:** capture the card, convert HOLD -> REDEEMED, booking CONFIRMED, publish `BookingConfirmed`.
6. **Failure at supplier:** void the card authorisation, RELEASE the points hold, booking FAILED, notify member.
7. **Timeouts/unknown supplier outcome:** don't compensate blindly; query supplier status, or park for reconciliation (Q4).
8. Hold expiry sweeper releases orphaned holds; daily reconciliation of ledger vs bookings vs payments.

**Trade-offs and what can go wrong**
- Capturing payment before supplier confirmation forces refunds (bad experience, fees).
- Points and cash refund rules on cancellation differ by programme; model them explicitly.
- Exchange-rate/points-value changes between quote and booking; honour the quote within TTL.

**How I'd monitor it**
Holds outstanding and their age, auth-without-capture counts, compensation rate, reconciliation mismatches (should be zero).

**Follow-ups to expect**
- *Why hold instead of debit?* -> Easy, clean release on failure; mirrors card authorisation.
- *Concurrency on balance?* -> Atomic conditional update (`UPDATE ... SET held = held + x WHERE available >= x`) or optimistic locking.
- *Partial refunds?* -> Separate ledger entries per refund with references.

**60-second answer**
"The quote fixes the split and a TTL. Booking runs as a saga: an atomic, idempotent points hold that also prevents double-spending from two devices, then a card authorisation, then the supplier booking. On success we capture the card and turn the hold into a redemption; on supplier failure we void the authorisation and release the hold. An unknown outcome is never compensated blindly; we check with the supplier or park it for reconciliation. A sweeper releases orphaned holds and a daily reconciliation matches ledger, payments and bookings."

### Q4 [senior] The supplier timed out during booking: did the booking happen? Handle unknown outcomes.
tags: unknown-outcome, timeouts, reconciliation, idempotency, supplier-integration, reliability, company-chase-travel

**Start here: the concepts**
- **Three outcomes:** success, failure, **unknown** (timeout after sending): the request may or may not have been processed.
- **Idempotent request reference:** lets you ask "what happened to request X?" or retry safely.
- **Reconciliation:** periodic comparison of our records with supplier records.

**The live scenario (functional requirement)**
*FR: "Never leave a member with a charged card and no room, or a room with no record on our side, even when a supplier's API times out mid-booking."*

**What the interviewer is really checking**
Rigour with distributed failure modes in third-party integrations.

**How I answer it**
1. Always send our **unique booking reference** to the supplier (many supplier APIs accept a client reference).
2. On timeout: mark booking **PENDING_CONFIRMATION**, do **not** release points or void payment yet.
3. **Status check:** query the supplier by our reference with backoff for a short window (e.g. up to 2 minutes).
4. Found -> continue as success. Confirmed absent -> retry booking if the quote is still valid, or compensate (release hold, void auth) and inform the member.
5. Still unknown -> keep the hold, show the member "confirmation in progress", escalate to an operations queue with all context.
6. **Daily reconciliation** with supplier booking reports catches orphan reservations on either side (cancel orphans at the supplier within free cancellation windows).
7. Choose supplier timeouts based on their real latency distribution; overly short timeouts create unknowns.

**Trade-offs and what can go wrong**
- Retrying a non-idempotent booking call can create duplicate reservations.
- Releasing holds too early lets members spend points that are actually used.
- Some suppliers lack status APIs; rely on reconciliation files and manual operations.

**How I'd monitor it**
PENDING_CONFIRMATION count and age, status-check outcomes, orphan bookings found by reconciliation, operations queue size.

**Follow-ups to expect**
- *What if the member retries meanwhile?* -> The same booking id is reused (idempotent), so no second booking.
- *Why not a longer timeout?* -> Long timeouts hold threads and hurt UX; prefer status checks.
- *Where's the state machine?* -> In the booking service; transitions guarded and audited.

**60-second answer**
"A timeout means unknown, not failure. We always send our own booking reference, so on timeout the booking goes to pending-confirmation, the points hold and card authorisation stay in place, and we poll the supplier's status by our reference for a couple of minutes. If it's there, we confirm; if it's definitely absent, we retry or compensate; if it's still unknown, the member sees 'confirmation in progress' and operations gets the case. Daily reconciliation against supplier reports catches any orphans on either side."

### Q5 [senior] Prices change between search and booking: design quotes, re-pricing and price-change handling.
tags: pricing, quotes, price-change, ttl, revalidation, user-experience, company-chase-travel

**Start here: the concepts**
- **Shopping price vs bookable price:** search often uses cached prices; the bookable price comes from a live check.
- **Quote:** a server-side record of a priced offer (supplier rate key, member price in points/cash, taxes, rules) with an expiry.

**The live scenario (functional requirement)**
*FR: "Members must never be charged more than what they confirmed; if the price changed, they must be told clearly and can accept or go back."*

**What the interviewer is really checking**
Correctness and trust in a volatile-pricing domain.

**How I answer it**
1. **Search:** prices labelled as "from" or current-as-of; cached.
2. **Select:** live re-price with the supplier -> create a **quote** (id, supplier rate token, member price, cancellation policy, expiry e.g. 15 minutes); price signed/stored server-side so the client can't tamper.
3. **Book:** reference the quote id; the booking service re-validates with the supplier just before booking.
4. **Price increased:** stop, return a `PRICE_CHANGED` Problem Details with old/new price; the UI asks the member to accept.
5. **Price decreased:** policy decision: usually pass the saving on (or keep quoted price, per programme rules).
6. **Quote expired:** re-price and show the new price.
7. Track price-change frequency per supplier/destination to tune cache TTLs.

**Trade-offs and what can go wrong**
- Too many price-change interruptions hurt conversion; fresher caches cost more supplier calls.
- Trusting a client-sent price is a fraud vector; always use the server-side quote.

**How I'd monitor it**
Price-change rate at booking, quote expiry rate, conversion after price change, supplier price accuracy.

**Follow-ups to expect**
- *Points price changes?* -> Points conversion is our rule; honour the quote within its TTL.
- *Taxes and fees?* -> Itemised in the quote; displayed per local regulations.
- *Why 409 vs 422 for price change?* -> A 409 conflict with the current state is common; document the code.

**60-second answer**
"Search shows cached prices, but selecting an offer triggers a live re-price that creates a server-side quote with the supplier rate token, the member price in points and cash, the cancellation policy and a 15-minute expiry. Booking references the quote id, never a client-sent price, and re-validates with the supplier just before booking. If the price went up, we stop with a clear PRICE_CHANGED error and the member decides. Expired quotes re-price, and price-change rates per supplier tune our cache TTLs."

### Q6 [senior] Model cancellations, changes and refunds as a booking state machine.
tags: state-machine, cancellations, refunds, booking-lifecycle, compensation, domain-modeling, company-chase-travel

**Start here: the concepts**
- **Booking lifecycle states** and allowed transitions, enforced in one place.
- **Supplier policies:** free cancellation until a deadline, penalties, non-refundable rates; airline changes with fare differences.
- **Refund routing:** points back to the ledger, cash back to the original card, possibly split.

**The live scenario (functional requirement)**
*FR: "Members can cancel or change bookings online; refunds follow the supplier policy and the original payment split; agents see the full history; schedule changes from airlines trigger customer notifications and options."*

**What the interviewer is really checking**
Rich domain modelling with external policies and money flows.

**How I answer it**
1. **States:** QUOTED -> HELD -> CONFIRMED -> (TICKETED for air) -> CHANGE_PENDING -> CHANGED; CANCELLATION_PENDING -> CANCELLED; REFUND_PENDING -> REFUNDED/PARTIALLY_REFUNDED; FAILED.
2. **Transitions** in one aggregate with guards (can't cancel a CANCELLED booking; can't refund before supplier cancellation is confirmed); every transition persisted and audited, with an event published.
3. **Cancellation flow:** fetch current policy and penalty from the supplier -> show the member the refund (points X, cash Y) -> confirm -> supplier cancel -> refund saga (ledger refund entry, card refund) -> notifications.
4. **Refund split rule:** penalties applied first to cash or points per programme rules, made explicit and tested.
5. **Changes:** treated as cancel+rebook or supplier "modify" depending on capability; price differences settled with additional charge or refund.
6. **Supplier-initiated changes** (airline schedule changes) arrive as events -> booking flagged -> member notified with options.

**Trade-offs and what can go wrong**
- Time zones and policy deadlines (hotel-local time) cause wrongful penalties.
- Partial failures (supplier cancelled, refund failed) need retries and operations visibility.

**How I'd monitor it**
Cancellations by reason, refund latency, stuck *_PENDING states, penalty disputes, schedule-change handling time.

**Follow-ups to expect**
- *Why explicit states?* -> Prevents illegal transitions and makes support and audit straightforward.
- *Event sourcing here?* -> Useful for full history; an audit table is often enough.
- *Refund to an expired card?* -> Card networks generally route to the replacement account; otherwise operations handles it.

**60-second answer**
"The booking is an aggregate with explicit states and guarded transitions, confirmed, cancellation-pending, cancelled, refund-pending, refunded and so on, each persisted, audited and published as an event. Cancelling fetches the live supplier policy, shows the member exactly how much comes back in points and cash, then runs the supplier cancellation and a refund saga to the ledger and the card. Penalty allocation rules are explicit and tested, deadlines use the hotel's local time, and airline schedule changes arrive as events that flag the booking and notify the member."

### Q7 [senior] Protect card and passport data: PCI DSS scope reduction and PII handling.
tags: pci-dss, tokenization, pii, data-protection, encryption, compliance, company-chase-travel

**Start here: the concepts**
- **PCI DSS (v4.0.1 current):** rules for systems that store, process or transmit cardholder data; **scope** = every system touching it.
- **Tokenisation:** replace the card number (PAN) with a token; only the vault/payment provider can map back.
- **Travel PII:** passport numbers, dates of birth, Secure Flight / APIS data for airlines, loyalty numbers.

**The live scenario (functional requirement)**
*FR: "Members pay with stored or new cards and enter passport details for international flights; the platform must pass PCI and privacy audits, and most microservices must stay out of PCI scope."*

**What the interviewer is really checking**
Architecture that minimises sensitive data exposure, not just encryption buzzwords.

**How I answer it**
1. **Card capture** via hosted fields/iframe or SDK from the payment provider: the PAN goes directly to the provider's vault; our services only see **tokens**. That keeps most services out of PCI scope.
2. **A small payment service** in a segmented network zone uses tokens with the processor; it's the only component in heavier PCI scope.
3. **Passport/PII:** stored encrypted at field level (envelope encryption with KMS keys), accessed only by fulfilment services that need it, masked in UIs and logs; retention limited to what travel rules require.
4. **Logs and events:** never contain PAN/CVV (CVV is never stored at all); PII masked; DLP scanning on log pipelines.
5. **Access:** least privilege, audited access to PII, break-glass procedures for agents.
6. **AI features:** prompts never include card data; PII redacted before any model call.
7. **Testing:** synthetic data in non-prod; never production PII in test environments.

**Trade-offs and what can go wrong**
- Field-level encryption complicates search/reporting; use tokenised or hashed lookups.
- Debug logging accidentally capturing request bodies is a classic PCI breach.

**How I'd monitor it**
DLP alerts in logs, access audit anomalies, key rotation status, quarterly scans and pen-test findings.

**Follow-ups to expect**
- *Can we store CVV?* -> No, never after authorisation.
- *Network segmentation?* -> Separate the cardholder data environment; strict ingress/egress.
- *Data residency?* -> Store PII in required regions; replicate carefully.

**60-second answer**
"I shrink PCI scope by design: card details are captured by the payment provider's hosted fields or SDK, so the card number goes straight to their vault and our services only handle tokens. One small payment service in a segmented zone talks to the processor. Passport and other PII are field-level encrypted with KMS, readable only by fulfilment, masked in UIs and logs and kept no longer than needed. CVV is never stored, logs are DLP-scanned, non-prod uses synthetic data, and AI prompts never carry card or passport data."

### Q8 [architect] Handle a promotional traffic spike of 5 to 10 times normal load.
tags: peak-traffic, autoscaling, load-shedding, caching, queueing, capacity, company-chase-travel

**Start here: the concepts**
- **Planned peaks:** promotions, holiday booking seasons, partner campaigns: known in advance.
- **Protection layers:** CDN and caches, autoscaling and pre-scaling, rate limits, queues/virtual waiting rooms, load shedding, graceful degradation.

**The live scenario (functional requirement)**
*FR: "A card-member promotion launches at 10:00 with limited discounted inventory; expect 10× normal traffic for an hour; bookings must stay correct and the site must stay up."*

**What the interviewer is really checking**
Capacity planning plus protective design for both your systems and suppliers.

**How I answer it**
1. **Plan:** traffic forecast with marketing; load test at 10×+ (Q14 in the migration pack); identify the bottleneck (often suppliers or the points ledger).
2. **Pre-scale** services and nodes 30 minutes before launch; warm caches (promo inventory, content) and JVMs.
3. **Edge:** CDN for static and content; a **virtual waiting room** if demand exceeds safe capacity (fair queueing at the edge).
4. **Inventory correctness:** limited promo inventory counted atomically (Redis/DB conditional decrement) with holds and expiry; no overselling.
5. **Supplier protection:** per-supplier rate limits, request coalescing for identical searches, cache shared availability.
6. **Degrade gracefully:** turn off non-essential features (recommendations, AI assistant suggestions) via flags; serve cached search results.
7. **Booking path priority:** separate capacity (bulkheads) so search spikes don't starve bookings.
8. War room with live business dashboards; rollback/kill switches ready.

**Trade-offs and what can go wrong**
- Autoscaling alone reacts too slowly for a 10:00 spike; pre-scale.
- Waiting rooms frustrate users but protect correctness and availability.
- Over-caching promo prices leads to selling expired offers; tight TTLs for promo items.

**How I'd monitor it**
Real-time RPS, latency, error rates, booking success, inventory remaining, supplier errors, queue length in the waiting room.

**Follow-ups to expect**
- *Thundering herd at 10:00:00?* -> Waiting room with randomised admission; cache warm-up.
- *Why separate booking capacity?* -> Revenue path must survive search overload.
- *Post-event?* -> Review against forecast; feed capacity model.

**60-second answer**
"It's a planned peak, so I plan: forecast with marketing, load test past 10x and find the real bottleneck, usually suppliers or the points ledger. Pre-scale and warm caches and JVMs before 10:00, put content on the CDN and a virtual waiting room in front if demand exceeds safe capacity. Limited promo inventory is decremented atomically with holds so nothing oversells. Suppliers are protected with rate limits and request coalescing, non-essential features switch off by flag, and booking capacity is isolated from search, with a war room on live dashboards."

### Q9 [senior] Monitor a booking platform: which business and technical signals matter, and how do you run incidents?
tags: observability, business-kpis, slo, incident-management, splunk, supplier-monitoring, company-chase-travel

**Start here: the concepts**
- **Business KPIs** detect problems technical metrics miss: booking success rate, look-to-book, payment failure rate.
- **SLOs** per user journey (search, book, cancel) with error budgets.
- **Incident management:** detection, triage, mitigation, communication, post-incident review.

**The live scenario (functional requirement)**
*FR: "Detect within 5 minutes when one hotel supplier starts failing bookings in one market, route around it, and tell customer service, before social media notices."*

**What the interviewer is really checking**
Practical observability tied to business impact, and incident leadership.

**How I answer it**
1. **Business metrics** per supplier/market/channel: bookings per minute vs same time last week, booking success rate, price-change rate, payment declines, points redemption failures.
2. **Technical:** RED metrics per service and supplier adapter, breaker states, Kafka lag, DB health; traces from search to booking.
3. **Alerting:** anomaly detection on bookings per minute and success rate per supplier (seasonality-aware), SLO burn-rate alerts; alerts include runbook links.
4. **Mitigation tools:** feature flag to disable a supplier per market (search stops showing it), fallback to alternative suppliers, cached content.
5. **Incident process:** incident commander, comms lead (customer service briefed with a script), status page; timeline captured.
6. **Post-incident review:** blameless, root cause and contributing factors, actions with owners (e.g. supplier-specific health checks, contract escalation).
7. Logs in Splunk (or similar) with booking id, supplier, market fields for fast searches.

**Trade-offs and what can go wrong**
- Alert fatigue from static thresholds; use baselines and SLOs.
- Supplier failures can be silent (200 OK with error payloads); parse and count business errors.

**How I'd monitor it**
That's the design: supplier health dashboard, journey SLOs, business anomaly alerts, MTTD/MTTR trends.

**Follow-ups to expect**
- *Silent failures?* -> Synthetic bookings against supplier test environments, and business-level error parsing.
- *Who decides to disable a supplier?* -> Pre-agreed runbook authority for on-call, with product informed.
- *Metrics for the AI assistant?* -> Containment rate, escalation rate, answer quality, cost.

**60-second answer**
"Business metrics catch what technical ones miss, so I track bookings per minute and success rate per supplier, market and channel against seasonal baselines, alongside RED metrics, breaker states and traces. Anomaly and SLO burn-rate alerts link to runbooks. The key mitigation is a flag that disables a supplier per market so search routes around it. Incidents have a commander and a comms lead who briefs customer service with a script, and blameless reviews produce owned actions. Logs carry booking, supplier and market fields for fast searches."

### Q10 [architect] Add a GenAI trip-planning assistant to the travel platform safely.
tags: genai, trip-planner, rag, mcp, tool-calling, guardrails, company-chase-travel

**Start here: the concepts**
- **RAG** over destination content, policies and FAQs; **tools** (search, price, booking) via function calling or **MCP servers**; **guardrails** around actions involving money or points.

**The live scenario (functional requirement)**
*FR: "A member types 'A 4-night beach trip in December for two, under 120,000 points, near good snorkelling'; the assistant proposes options with real availability and prices, answers policy questions, and can start a booking that the member confirms."*

**What the interviewer is really checking**
A design that combines RAG, tools, the existing platform and safety, within cost and latency limits.

**How I answer it**
1. **Assistant service** (Spring Boot + Spring AI or LangChain4j) behind the BFF, streaming responses over SSE.
2. **Understanding:** the model extracts structured intent (dates, travellers, budget in points, preferences) as validated JSON.
3. **Knowledge (RAG):** destination guides, hotel content and amenities, programme FAQs and cancellation policies, embedded in a vector store with metadata (region, property id, language).
4. **Live data via tools:** `searchHotels`, `getQuote`, `getPointsBalance`, `startBooking`: exposed by the platform's own services through **MCP servers** or direct tools; tools act with the **member's identity**.
5. **Grounding:** prices and availability only from tool results, never generated; quotes shown with their expiry.
6. **Booking safety:** `startBooking` creates a draft; the member reviews and confirms in the normal UI flow (human-in-the-loop); the assistant can't spend points by itself.
7. **Guardrails:** topic limits, prompt-injection defences (hotel content is untrusted input), PII minimisation, no card data in prompts.
8. **Cost/latency:** small model for intent extraction, larger model for itinerary composition; cache destination answers; cap tool iterations.
9. **Evaluation & monitoring:** golden scenarios, task success, conversion, escalation, cost per conversation.

**Trade-offs and what can go wrong**
- Hallucinated amenities or prices damage trust; ground in content and tools, cite sources.
- Supplier search costs explode if the agent searches too broadly; limit and cache.
- Regulatory/brand risk; human review of prompts, launch with limited audience.

**How I'd monitor it**
Conversation success and conversion, tool error rates, iterations per conversation, cost per conversation, guardrail triggers, member feedback.

**Follow-ups to expect**
- *Why MCP here?* -> The same tool servers serve the member assistant, the agent-desktop copilot and internal tools.
- *Personalisation and privacy?* -> Use member preferences with consent; no sensitive data in prompts.
- *Multilingual?* -> Embeddings and models that support the target languages; evaluate per language.

**60-second answer**
"A Spring AI assistant service streams answers through the BFF. The model first extracts structured intent: dates, travellers, points budget, preferences. Destination content and programme policies come from RAG, while availability, prices and the points balance come only from tools the platform exposes, ideally as MCP servers acting with the member's identity, so prices are never invented. Booking creates a draft the member confirms in the normal flow. Guardrails treat hotel content as untrusted, keep card data out of prompts, cap tool iterations, and I measure task success, conversion and cost per conversation."
