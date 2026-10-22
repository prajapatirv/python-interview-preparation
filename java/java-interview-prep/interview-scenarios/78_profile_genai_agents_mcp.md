---
id: profile-java-genai-agents-mcp
title: Java + GenAI profile (9/9): GenAI architecture II, tool calling, MCP servers, agents and LLMOps (12 questions)
stack: java
skill: genai
---
Part of the **Java/J2EE + Gen AI** profile pack (see `../profile-java-genai/README.md`). GenAI questions 14–25 of 25.

Vendor-neutral: Spring AI 2.0 / LangChain4j 1.x against any OpenAI-compatible, Azure, Bedrock, Vertex or local Ollama/vLLM model.
**MCP facts are as of the 2026-07-28 specification revision**, which made the protocol stateless. SDKs adopt new revisions
over time, so check which protocol version your Spring AI / MCP Java SDK supports.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [senior] How does tool (function) calling work, and how do you implement it in Java?
tags: tool-calling, function-calling, spring-ai, langchain4j, tools, agents, profile-java-genai

**Start here: the concepts**
- **Tool calling:** you describe tools (name, description, JSON schema of parameters) to the model; the model may reply with a **tool call request** instead of text; **your application executes** the tool and sends the result back; the model then answers.
- The model never runs code or touches systems itself; the app is in control.
- **Spring AI:** methods annotated `@Tool` (+ `@ToolParam`) passed with `.tools(...)`. **LangChain4j:** `@Tool` methods registered on an AI Service.

**The live scenario (functional requirement)**
*FR: "Customers ask the travel assistant 'Where is my booking B123 and can I add a bag?'; the answer must use live booking data and the real baggage price."*

**What the interviewer is really checking**
The request/response loop, security of tool execution, and good tool design.

**How I answer it**
1. Define tools in a Spring bean:

```java
class BookingTools {
    @Tool(description = "Get status and itinerary of a booking owned by the current customer")
    BookingView getBooking(@ToolParam(description = "Booking reference like B123") String ref) { ... }
    @Tool(description = "Quote the price of adding checked bags to a booking")
    Quote quoteBags(String ref, int bags) { ... }
}
String reply = chatClient.prompt().user(question).tools(bookingTools).call().content();
```

2. Flow: model asks for `getBooking("B123")` -> Spring AI executes it -> result JSON goes back -> model may call `quoteBags` -> final answer.
3. **Authorisation inside the tool:** use the authenticated customer from the security context, not a customer id the model provides. The model's arguments are untrusted input; validate them.
4. **Read vs write:** quoting is safe; *adding* a bag (a payment) requires explicit user confirmation in the UI before execution (human-in-the-loop).
5. **Good tool design:** few, clearly named tools with precise descriptions; return compact JSON; meaningful errors the model can act on ("booking not found").
6. Limit tool-call iterations and total time per request.

**Trade-offs and what can go wrong**
- Too many similar tools confuse the model and inflate prompt tokens.
- Tools returning huge payloads blow the context window.
- Prompt injection can make the model call tools with harmful arguments; authorisation and confirmation stop real damage.

**How I'd monitor it**
Tool calls per request, tool error rates, iterations per request, latency per tool, blocked/confirmed write actions.

**Follow-ups to expect**
- *Who executes the tool?* -> The application; the model only proposes a call.
- *Parallel tool calls?* -> Many models can request several at once; execute concurrently if independent.
- *Tool calling vs MCP?* -> Tool calling is the model mechanism; MCP is a protocol for exposing tools from separate servers to any AI host.

**60-second answer**
"I describe tools to the model with a name, a description and a parameter schema; the model can answer with a tool-call request, my application executes it and sends back the result, and the model writes the final answer. In Spring AI that's `@Tool` methods passed with `.tools()`. The model's arguments are untrusted, so each tool authorises with the logged-in customer from the security context, and anything that spends money needs explicit user confirmation. I keep tools few and precise, payloads small, and iterations capped."

### Q2 [senior] What is the Model Context Protocol (MCP), and how is it structured?
tags: mcp, model-context-protocol, tools, resources, prompts, transports, json-rpc, profile-java-genai

**Start here: the concepts**
- **MCP:** an open protocol (introduced by Anthropic in late 2024, now widely adopted across vendors and IDEs) that standardises how AI applications connect to tools and data. "One protocol instead of N×M custom integrations."
- **Roles:** **host** (the AI application, e.g. an IDE assistant or your chat app) contains **clients**, each connected to an **MCP server** that exposes capabilities.
- **Server primitives:** **tools** (functions the model can call), **resources** (readable data identified by URIs), **prompts** (reusable prompt templates the user picks).
- **Wire format:** JSON-RPC 2.0. **Transports:** **stdio** (local process) and **Streamable HTTP** (remote). The old HTTP+SSE transport is deprecated.
- **2026-07-28 revision:** the protocol is now **stateless**: no `initialize` handshake or `Mcp-Session-Id`; every request carries protocol version and client capabilities in `_meta`; a `server/discover` call advertises versions and capabilities; server-initiated requests were replaced by the **multi round-trip request** pattern; Roots, Sampling and Logging are deprecated.

**The live scenario (functional requirement)**
*FR: "Our order, inventory and CRM systems must be usable by several AI clients (the internal chat assistant, developers' IDE assistants, and an agent platform) without writing a separate integration for each."*

**What the interviewer is really checking**
Clear understanding of roles, primitives, transports and why MCP matters architecturally.

**How I answer it**
1. Without MCP, each AI client needs custom tool code for each system: N clients × M systems.
2. With MCP, we build **one MCP server per domain** (orders, inventory, CRM) exposing tools like `findOrder`, `checkStock`, resources like `crm://customers/{id}`, and prompts like "summarise account".
3. Any MCP-capable host connects with a client: our Spring AI chat app (MCP client starter turns server tools into `ToolCallback`s), IDE assistants, agent platforms.
4. **Transport:** Streamable HTTP for shared remote servers behind the gateway; stdio for local developer tools.
5. **Statelessness (2026-07-28)** means MCP servers scale like ordinary stateless HTTP services behind a load balancer; cross-call state is passed explicitly as handles in tool arguments.
6. Security: OAuth 2.1-based authorisation for HTTP servers (Q4).

**Trade-offs and what can go wrong**
- MCP standardises the plumbing, not the quality of tool design or security.
- Exposing too many tools to a model degrades tool selection; hosts should let users enable only what they need.
- Spec evolves quickly; pin and test protocol versions between clients and servers.

**How I'd monitor it**
Tool calls per server and client, error rates, latency, authorisation failures, protocol version mismatches.

**Follow-ups to expect**
- *Tools vs resources?* -> Tools are actions the model invokes; resources are data the application reads and attaches to context.
- *MCP vs REST?* -> MCP servers usually wrap existing REST APIs, adding AI-friendly descriptions, schemas and discovery.
- *Why stateless now?* -> Easier horizontal scaling and routing; no sticky sessions.

**60-second answer**
"MCP is an open protocol that standardises how AI applications reach tools and data. A host, like our chat app or an IDE assistant, runs clients that connect to MCP servers, and servers expose tools the model can call, resources it can read and prompt templates. It's JSON-RPC over stdio locally or Streamable HTTP remotely. So instead of every AI client integrating every system, we build one MCP server per domain and any compliant host can use it. Since the 2026-07-28 revision the protocol is stateless, so servers scale like ordinary HTTP services."

### Q3 [senior] Build an MCP server in Spring Boot that exposes order-lookup tools.
tags: mcp-server, spring-ai, mcptool, streamable-http, spring-boot, implementation, profile-java-genai

**Start here: the concepts**
- **Spring AI MCP server starters:** `spring-ai-starter-mcp-server` (stdio), `spring-ai-starter-mcp-server-webmvc` / `-webflux` (HTTP).
- **Annotations:** `@McpTool` + `@McpToolParam`, `@McpResource` (URI templates), `@McpPrompt`, `@McpComplete`; discovered automatically from beans.
- **Protocol property:** `spring.ai.mcp.server.protocol=STREAMABLE` or `STATELESS` (SSE is deprecated in Spring AI 2.0).

**The live scenario (functional requirement)**
*FR: "Expose 'find order', 'order status history' and 'initiate return' as MCP tools for internal AI assistants; returns need human approval; only authenticated employees can use it."*

**What the interviewer is really checking**
Hands-on implementation plus production concerns: auth, input validation, write safety.

**How I answer it**
1. Dependency `spring-ai-starter-mcp-server-webmvc`; properties: server name/version, `protocol: STATELESS` (scales horizontally).
2. Tools:

```java
@Component class OrderMcpTools {
    @McpTool(name = "find_order", description = "Find an order by order number; returns status, items, dates")
    OrderSummary findOrder(@McpToolParam(description = "Order number, e.g. ORD-10293", required = true) String orderNo) {
        return orderService.summary(validate(orderNo));
    }
}
```

   A resource like `@McpResource(uri = "orders://{orderNo}/timeline")` exposes the status history as readable context.
3. **Writes:** `initiate_return` creates a **pending return request** that a human approves in the back office, rather than executing the return directly; the tool description says so.
4. **Security:** the HTTP transport is **unauthenticated by default**, so put Spring Security in front: the server is an **OAuth2 resource server** validating tokens issued for this MCP server (audience), with scopes per tool (`orders:read`, `returns:create`).
5. Reuse existing domain services (the MCP layer is an adapter, like a REST controller).
6. Return compact DTOs, clear error messages; log every tool call with user, tool and arguments (redacted).
7. Test with the MCP Inspector and integration tests using the MCP Java client.

**Trade-offs and what can go wrong**
- Exposing raw internal APIs 1:1 gives the model confusing, low-level tools; design task-level tools.
- Unauthenticated HTTP endpoints = anyone on the network can call every tool.
- Large responses blow up the client's context.

**How I'd monitor it**
Calls per tool and per client app, error and latency, auth failures, pending-approval queue for returns.

**Follow-ups to expect**
- *Stdio or HTTP?* -> Stdio for local single-user tools; HTTP for shared enterprise servers.
- *Sync vs async server?* -> `spring.ai.mcp.server.type=SYNC` (default) or `ASYNC` for reactive methods.
- *How does a Spring AI client consume it?* -> The MCP client starter registers the server's tools as tool callbacks for `ChatClient`.

**60-second answer**
"I add Spring AI's WebMVC MCP server starter in stateless Streamable HTTP mode, and annotate methods in a component with `@McpTool` and `@McpToolParam`: find order, status history as a resource. Under the hood they call the existing domain services, so MCP is just another adapter. 'Initiate return' only creates a pending request a human approves. The HTTP transport is unauthenticated by default, so Spring Security makes it an OAuth2 resource server with per-tool scopes, and every call is audited."

### Q4 [architect] Secure MCP servers and AI tool use in an enterprise.
tags: mcp-security, oauth-2-1, tool-poisoning, prompt-injection, least-privilege, confused-deputy, profile-java-genai

**Start here: the concepts**
- **MCP authorization (HTTP transports):** based on **OAuth 2.1**; the MCP server acts as a resource server, advertises its authorization server via protected resource metadata; clients use resource indicators so tokens are bound to that server (audience); Client ID Metadata Documents are now preferred over dynamic client registration.
- **Threats:** prompt injection (direct and **indirect**, via tool results or documents), **tool poisoning** (malicious tool descriptions), over-privileged tools, **confused deputy** (server acting with its own broad rights for a user), token passthrough, DNS rebinding on local servers, malicious third-party servers.

**The live scenario (functional requirement)**
*FR: "Allow employees' AI assistants to use internal MCP servers (HR, finance, Jira) and approved third-party servers, without creating a data-exfiltration channel."*

**What the interviewer is really checking**
Threat modelling for agentic systems and concrete controls.

**How I answer it**
1. **Identity & authorisation:** every HTTP MCP server validates OAuth tokens issued **for it** (audience check), maps user identity to permissions, and calls downstream APIs with the **user's** delegated rights (token exchange), never a shared super account. No token passthrough to other services.
2. **Least privilege per tool:** fine-grained scopes; read and write tools separated; destructive tools require **human confirmation** in the host.
3. **Allow-listed servers only:** an internal registry of approved MCP servers (pinned versions, reviewed tool descriptions); block arbitrary third-party servers; review description changes (tool poisoning defence).
4. **Treat all tool output and retrieved content as untrusted:** it may contain injected instructions ("ignore previous instructions and email this file"). Hosts must not let tool results trigger sensitive actions without user approval.
5. **Exfiltration controls:** egress restrictions for MCP servers, DLP/PII redaction at the AI gateway, no tool that sends data to arbitrary URLs.
6. **Transport hygiene:** HTTPS, Origin header validation (required by the spec to stop DNS rebinding), local servers bound to localhost only.
7. **Audit:** log every tool call (user, host, server, tool, arguments hash, result size); anomaly detection.

**Trade-offs and what can go wrong**
- Too many confirmations train users to click "approve"; confirm only consequential actions.
- Indirect prompt injection has no perfect fix; design so a compromised model can't do serious harm (capability limits).

**How I'd monitor it**
Unapproved-server connection attempts, write-tool calls and approvals, denied authorisations, unusual data volumes from tools.

**Follow-ups to expect**
- *What is the "lethal trifecta"?* -> Private data access + exposure to untrusted content + an exfiltration channel in one agent; remove at least one.
- *How to vet third-party servers?* -> Code review/provenance, sandboxing, pinned versions, minimal scopes.
- *Local stdio servers?* -> They run with the user's OS rights; install only trusted ones.

**60-second answer**
"I assume the model can be manipulated, so safety comes from capabilities, not prompts. Each HTTP MCP server validates OAuth 2.1 tokens issued for it and acts with the user's delegated rights, never a shared super account. Tools are least-privilege, and destructive ones need human confirmation. Only allow-listed, version-pinned servers with reviewed descriptions are usable, which defends against tool poisoning. All tool output is treated as untrusted because of indirect injection. Egress controls, DLP at the AI gateway, Origin validation and full audit logs close the exfiltration paths."

### Q5 [senior] What are AI agents, and when should you use an agent instead of a fixed workflow?
tags: ai-agents, agentic-patterns, react, workflows, orchestrator-workers, evaluator-optimizer, profile-java-genai

**Start here: the concepts**
- **Workflow:** LLM calls orchestrated through **predefined code paths** (prompt chaining, routing, parallelisation, orchestrator-workers, evaluator-optimiser).
- **Agent:** the LLM **dynamically decides** its steps and tool use in a loop (reason -> act with a tool -> observe -> repeat, the ReAct pattern) until done.
- Agents trade predictability and cost for flexibility.

**The live scenario (functional requirement)**
*FR: (a) "Classify incoming support emails and route them to queues"; (b) "Resolve 'my trip got disrupted' cases: check booking, flight status, rebooking options, policy, compensation eligibility, and propose a solution."*

**What the interviewer is really checking**
Judgement: the simplest pattern that works, with guardrails on autonomy.

**How I answer it**
1. **(a) is a workflow:** one classification call (structured output) + routing code. Predictable, cheap, testable. No agent.
2. **(b) has variable paths** (cancelled vs delayed, hotel needed or not, policy differences): an **agent** with tools `getBooking`, `getFlightStatus`, `searchRebooking`, `checkPolicy`, `calculateCompensation`.
3. **Guardrails on the loop:** max iterations (e.g. 8), timeout, token budget; tools read-only except `proposeRebooking`, which the customer or an agent must confirm.
4. **Hybrid:** deterministic steps stay in code (always fetch booking first; always run the policy check before offering compensation); the agent decides the rest.
5. In Java: Spring AI `ChatClient` with tools (the tool-calling loop is the agent loop), or LangChain4j AI Services/agentic modules; workflow engines for durable long-running flows.
6. Evaluate on recorded scenarios: success rate, steps, cost.

**Trade-offs and what can go wrong**
- Agents loop, take odd paths, and cost more; hard to test.
- Errors compound across steps; each tool must return clear errors.
- Autonomy over write actions needs human approval.

**How I'd monitor it**
Task success rate, steps and tokens per task, loop/timeout terminations, human-override rate, cost per resolved case.

**Follow-ups to expect**
- *Prompt chaining?* -> Fixed sequence of LLM calls, each using the previous output.
- *Evaluator-optimiser?* -> One call generates, another critiques, repeat until criteria pass.
- *Durable agents?* -> Persist state between steps (workflow engine) for long-running or human-wait steps.

**60-second answer**
"A workflow runs LLM calls through code paths I define; an agent lets the model choose its steps and tools in a loop. I use the simplest thing that works: routing support emails is one classification call plus code, no agent. Disrupted-trip resolution has genuinely variable paths, so an agent with booking, flight status, rebooking, policy and compensation tools fits, with mandatory steps kept in code, an iteration cap, a token budget, and confirmation before any rebooking. I measure success rate, steps and cost per case."

### Q6 [architect] Design a multi-agent system, and explain where protocols like MCP and A2A fit.
tags: multi-agent, a2a, mcp, orchestration, agent-architecture, interoperability, profile-java-genai

**Start here: the concepts**
- **Multi-agent:** several specialised agents (each with its own prompt, tools and model) coordinated by an orchestrator or by handoffs.
- **MCP:** agent <-> tools/data ("vertical" integration).
- **A2A (Agent2Agent protocol):** agent <-> agent ("horizontal"): agents publish an **Agent Card** describing skills and endpoint, and exchange **tasks** and messages over HTTP. Originated at Google (2025) and is now under the Linux Foundation.

**The live scenario (functional requirement)**
*FR: "Corporate travel requests ('Book me to the Berlin conference, within policy, and arrange a visa letter') should be handled by a travel agent, a policy-compliance agent and an HR/visa agent owned by different teams."*

**What the interviewer is really checking**
Whether you can justify multiple agents and design coordination, interfaces and failure handling.

**How I answer it**
1. **Justify:** separate teams, separate data access and different responsibilities; a single agent with 40 tools would be confused and over-privileged.
2. **Orchestrator (supervisor) agent** parses the request into tasks and delegates: travel options -> policy check -> booking proposal -> visa letter.
3. **Each specialist** uses **MCP** to reach its own systems (booking engine, policy rules, HR system) with its own permissions.
4. **Between agents owned by different teams/platforms**, use **A2A**: each publishes an Agent Card; the orchestrator sends tasks and tracks their state (submitted, working, input-required, completed). Inside one codebase, plain method calls or events are simpler.
5. **Deterministic guardrails:** policy compliance is a rules engine call, not an LLM opinion; booking requires the traveller's confirmation.
6. **State and durability:** the overall request is a persisted workflow (it may wait days for a manager's approval).
7. **Observability:** one trace across agents; per-agent cost and success.

**Trade-offs and what can go wrong**
- Multi-agent systems multiply cost, latency and failure modes; start with one agent + tools, split when needed.
- Agents talking in free text lose information; use structured task payloads.
- Protocols are young and evolving; isolate them behind adapters.

**How I'd monitor it**
End-to-end success, handoffs per request, per-agent latency/cost/error, stuck tasks in input-required state.

**Follow-ups to expect**
- *MCP vs A2A in one line?* -> MCP connects an agent to tools and data; A2A connects agents to other agents.
- *Java support?* -> Spring AI / LangChain4j for agents and MCP; A2A has Java SDKs and integrations in the ecosystem.
- *Supervisor vs swarm?* -> Supervisor is central and easier to control; swarm/handoffs are decentralised.

**60-second answer**
"I'd only split into multiple agents when ownership, data access or responsibilities differ, which they do here: travel, policy and HR teams. A supervisor agent breaks the request into tasks and delegates. Each specialist reaches its own systems through MCP with its own permissions, and agents owned by different teams talk through A2A, with Agent Cards describing skills and a task lifecycle including input-required. Policy compliance stays a deterministic rules call, booking needs the traveller's confirmation, and the whole request is a durable, traced workflow."

### Q7 [architect] Defend an LLM application against prompt injection, data leakage and unsafe output.
tags: guardrails, prompt-injection, pii, data-leakage, output-validation, owasp-llm-top-10, profile-java-genai

**Start here: the concepts**
- **OWASP Top 10 for LLM applications** (2025): prompt injection, sensitive information disclosure, supply chain, data/model poisoning, improper output handling, excessive agency, system prompt leakage, vector/embedding weaknesses, misinformation, unbounded consumption.
- **Direct injection** (user types it) vs **indirect injection** (hidden in documents, emails, web pages or tool results the model reads).
- **Guardrails:** input checks, output checks, capability limits, monitoring.

**The live scenario (functional requirement)**
*FR: "A customer-facing assistant with RAG over public help articles and tools to read the customer's own account data; it must not leak other customers' data, internal prompts, or produce unsafe/off-brand content."*

**What the interviewer is really checking**
Defence in depth, and knowing that prompts alone are not security.

**How I answer it**
1. **Capability limits first (most important):** tools act only on the authenticated customer's data; no tools that can email arbitrary addresses or fetch arbitrary URLs; write actions need confirmation. Then even a successful injection can't do much (limits *excessive agency*).
2. **Input guardrails:** length limits, PII detection/redaction before sending to the model when not needed, a classifier for obvious jailbreak/injection patterns, topic restriction.
3. **Retrieved content is data, not instructions:** delimit it clearly in the prompt and tell the model to ignore instructions inside it; sanitise ingested documents (strip hidden text).
4. **Output guardrails:** never render model output as raw HTML (XSS) or pass it to SQL/shell (*improper output handling*); validate structured outputs; moderation check for unsafe content; regex/DLP for leaked secrets or other customers' identifiers.
5. **System prompt:** assume it can leak; keep secrets and access rules out of it.
6. **Unbounded consumption:** rate limits, token caps, max tool iterations.
7. **Red-team suite** of injection prompts in CI; monitoring and incident response.

**Trade-offs and what can go wrong**
- Over-aggressive filters block legitimate customers.
- Classifier-based detection is probabilistic; never rely on it alone.
- Each guardrail adds latency; run cheap checks inline and heavy ones asynchronously or for high-risk flows.

**How I'd monitor it**
Blocked inputs/outputs by rule, injection attempts detected, PII redaction counts, red-team pass rate, user reports.

**Follow-ups to expect**
- *Why isn't "you must never reveal X" enough?* -> Models can be talked out of instructions; enforcement must be outside the model.
- *Guardrail frameworks?* -> Provider moderation APIs, open-source guard models and libraries; LangChain4j and Spring AI let you plug checks in as advisors/guardrails.
- *What is excessive agency?* -> Giving the model more tools, permissions or autonomy than the task needs.

**60-second answer**
"Prompts aren't security, so I start with capabilities: tools only touch the logged-in customer's data, nothing can send data to arbitrary destinations, and writes need confirmation, so even a successful injection does little. Then layers: input limits and PII redaction, retrieved documents clearly delimited as data and sanitised at ingest, outputs never rendered as raw HTML or executed, moderation and DLP checks on the way out, and token and iteration caps. Nothing secret goes in the system prompt, and an injection red-team suite runs in CI."

### Q8 [senior] Make GenAI features observable: what do you log, measure and trace?
tags: llm-observability, opentelemetry, token-usage, tracing, micrometer, llmops, profile-java-genai

**Start here: the concepts**
- **OpenTelemetry GenAI semantic conventions:** standard `gen_ai.*` attributes (system/provider, request model, token usage, operation).
- **Spring AI** emits Micrometer observations for chat, embedding, tool and vector-store calls, including token-usage metrics; prompt/completion content logging is off by default.
- **LLMOps:** operating LLM features: quality, cost, latency, safety, drift.

**The live scenario (functional requirement)**
*FR: "Product, finance and support must see, per feature: usage, cost per day, latency, failure rates, answer quality trends, and drill into any single bad answer a customer reports."*

**What the interviewer is really checking**
That you extend standard observability with LLM-specific signals, while respecting privacy.

**How I answer it**
1. **Traces:** one trace per request with spans: retrieval (with doc ids and scores), each LLM call (model, tokens in/out, latency, finish reason), each tool call, guardrail checks. Exported via OTLP.
2. **Metrics:** tokens and cost per feature/model/tenant, time to first token, total latency, error types (rate limits, timeouts, refusals, content filters), cache hit rate, tool iterations.
3. **Quality signals:** thumbs up/down, regenerate clicks, escalation to human, sampled LLM-judge faithfulness scores, "not found" rate.
4. **Content logging with care:** prompts and answers stored in a restricted store with PII redaction, retention limits and access control, linked by trace id, so support can replay a reported bad answer.
5. **Versioning:** record prompt version, model version, index version on every trace; quality changes can be attributed.
6. Dashboards per feature; alerts on cost anomalies, error spikes and quality drops. Specialised LLM observability tools (open-source or commercial) can sit on top of the same OTLP data.

**Trade-offs and what can go wrong**
- Logging full prompts can store personal data indefinitely; legal and security must agree.
- High-cardinality labels (prompt text, user id) in metrics; put those in traces/logs.
- Sampling may drop exactly the bad answer; keep 100% of negatively rated interactions.

**How I'd monitor it**
This is the monitoring design: feature dashboards, cost anomaly alerts, quality trend alerts, per-version comparisons.

**Follow-ups to expect**
- *What is finish reason?* -> Why generation stopped: completed, max tokens, content filter, tool call.
- *Drift?* -> Quality changes from new documents, user behaviour or silent model updates; pin model versions.
- *Cost attribution?* -> Tag calls with feature and tenant at the gateway or client.

**60-second answer**
"Every request is one trace: retrieval with doc ids and scores, each LLM call with model, tokens, latency and finish reason, every tool call and guardrail check, using the OpenTelemetry GenAI conventions that Spring AI's observations follow. Metrics track tokens and cost per feature and tenant, time to first token, rate-limit and timeout errors, cache hits. Quality comes from feedback, escalations and sampled judge scores. Prompts and answers go to a restricted, redacted, time-limited store linked by trace id, and every trace records prompt, model and index versions."

### Q9 [architect] Spring AI, LangChain4j, or calling model APIs directly: how do you choose?
tags: spring-ai, langchain4j, framework-selection, java, abstraction, architecture-decision, profile-java-genai

**Start here: the concepts**
- **Spring AI:** Spring-native: `ChatClient`, advisors (RAG, memory), `VectorStore` abstraction across many stores, tool calling, MCP client/server starters, observability via Micrometer, Boot auto-configuration.
- **LangChain4j:** framework-agnostic Java library (works in Spring, Quarkus, Micronaut, plain Java): **AI Services** (declarative interfaces), RAG building blocks, tools, memory, MCP client, agentic modules; rich integrations.
- **Direct SDK/HTTP:** provider SDKs or plain HTTP; full control, most code.

**The live scenario (functional requirement)**
*FR: "A Spring Boot microservices estate (40 services) is adding GenAI features across teams; we want consistency, observability, and freedom to change model providers."*

**What the interviewer is really checking**
A principled choice and awareness of the trade-offs.

**How I answer it**
1. **Spring Boot estate -> Spring AI as the default:** auto-configuration, properties-based provider switching, Micrometer/OTel observability out of the box, MCP server and client starters, consistent with how teams already build.
2. **LangChain4j** where its strengths matter: declarative AI Services style that teams like, specific integrations, Quarkus services, or advanced agentic/RAG modules; it also has Spring Boot starters, so both can coexist.
3. **Direct SDK** for a brand-new provider feature not yet abstracted, behind our own port interface.
4. Whichever framework: wrap GenAI behind **domain ports** (hexagonal), so framework or provider changes don't ripple through business code.
5. Provide a **company starter**: default advisors (logging, guardrails), gateway base URL, token tagging, retry/timeouts.

**Trade-offs and what can go wrong**
- Abstractions lag behind provider features by weeks.
- Both frameworks evolve fast (breaking changes between majors); pin versions and upgrade deliberately.
- Mixing both frameworks across teams fragments skills; set a default.

**How I'd monitor it**
Framework versions per service, upgrade lag, incidents attributed to framework bugs.

**Follow-ups to expect**
- *What is an advisor in Spring AI?* -> An interceptor around the chat call (like a filter) used for RAG, memory, logging, guardrails.
- *AI Services in LangChain4j?* -> You declare a Java interface with annotations; the framework implements it with LLM calls, tools, memory and RAG.
- *Python ecosystem gap?* -> Smaller than it was; Java now covers RAG, tools, MCP and agents well.

**60-second answer**
"In a Spring Boot estate I default to Spring AI: auto-configuration, provider switching through properties, Micrometer and OpenTelemetry observability, advisors for RAG and memory, and MCP starters, all in the style teams already know. LangChain4j is a strong alternative, especially for its declarative AI Services or outside Spring, and the two can coexist. Direct SDKs only for features not yet abstracted. Either way, GenAI sits behind domain ports and a company starter that adds guardrails, timeouts and token tagging, so changing framework or provider stays local."

### Q10 [architect] Present a reference architecture for an enterprise GenAI platform on Java microservices.
tags: reference-architecture, ai-gateway, rag-service, mcp, platform, genai-architecture, profile-java-genai

**Start here: the concepts**
- **Platform thinking:** shared capabilities (gateway, retrieval, ingestion, evaluation, observability) so product teams build features, not plumbing.
- **Building blocks:** AI gateway, model endpoints, ingestion pipeline, vector store, RAG/retrieval service, MCP tool servers, agent/orchestration layer, guardrails, evaluation, LLMOps observability.

**The live scenario (functional requirement)**
*FR: "Within a year, 10 product teams will ship GenAI features (support copilot, document summaries, travel assistant, internal knowledge search). Security, cost control and consistent quality are mandatory."*

**What the interviewer is really checking**
The ability to draw and justify the whole picture, with clear ownership and flows.

**How I answer it**
1. **Channels:** web/mobile/internal apps -> API gateway -> **feature services** (Spring Boot) owned by product teams.
2. **AI gateway** (platform-owned): single egress to models: authN per service, quotas and budgets per team, PII redaction, routing by data classification (self-hosted vs cloud models), fallback, caching, full usage logging.
3. **Model layer:** cloud model platforms + self-hosted open-weight models (vLLM on GPU nodes) behind OpenAI-compatible APIs.
4. **Knowledge layer:** event-driven **ingestion pipeline** (connectors -> parse -> chunk -> embed -> index, Kafka between stages) -> **vector + keyword store** with ACL metadata -> a **retrieval service** offering hybrid search + re-ranking via one API.
5. **Tools layer:** domain-owned **MCP servers** (orders, CRM, HR) wrapping existing APIs with OAuth and per-tool scopes; registry of approved servers.
6. **Orchestration:** feature services use Spring AI (ChatClient, advisors, tools) for RAG and agents; a workflow engine for long-running flows with human approval.
7. **Cross-cutting:** guardrails library/starter, evaluation service (golden sets, CI gates), observability (OTel traces, cost dashboards), prompt and model version registry, secrets in vault, all on Kubernetes with GitOps.
8. **Governance:** AI use-case review, data classification, model approval list, incident process.

**Trade-offs and what can go wrong**
- A platform built before real use cases becomes shelfware; grow it from the first two features.
- Centralised gateway is a critical dependency: multi-replica, multi-zone, fail-safe policies.
- Teams bypassing the gateway with direct keys break cost and security controls; block egress.

**How I'd monitor it**
Per-team cost and budgets, platform SLOs (gateway latency, retrieval latency), feature quality scores, adoption metrics.

**Follow-ups to expect**
- *What does the retrieval service own?* -> Query rewriting, hybrid search, re-ranking, ACL filters: consistent quality for all teams.
- *Where do prompts live?* -> Versioned in git with the feature, or a prompt registry, always evaluated before release.
- *Build vs buy?* -> Buy commodity (gateway, vector store, observability) where possible; build the domain-specific parts.

**60-second answer**
"Product teams own Spring Boot feature services; the platform owns the shared pieces. An AI gateway is the only path to models, handling auth, team budgets, PII redaction, routing by data class between cloud and self-hosted models, fallback and usage logs. An event-driven ingestion pipeline feeds a hybrid vector-and-keyword store with ACLs, behind one retrieval service doing re-ranking and filters. Domain teams expose tools as OAuth-secured MCP servers from an approved registry. Guardrails, evaluation gates, OpenTelemetry tracing and cost dashboards are shared starters, all on Kubernetes with GitOps."

### Q11 [senior] How do you test GenAI features when outputs are non-deterministic?
tags: testing, llm-testing, mocks, evaluation, regression, contract-tests, profile-java-genai

**Start here: the concepts**
- **Deterministic layer:** everything around the model (prompt building, retrieval, tool execution, parsing, guardrails) is normal code, so test it normally.
- **Model behaviour:** tested statistically with evaluation sets and thresholds, not exact-match assertions.

**The live scenario (functional requirement)**
*FR: "The claims assistant goes through CI/CD like any service; a prompt tweak must not silently break extraction accuracy or start leaking data."*

**What the interviewer is really checking**
A layered test strategy that keeps CI fast and reliable.

**How I answer it**
1. **Unit tests (no model):** prompt templates render correctly, retrieval filters built from the user identity, tool authorisation, output parsing and validation, guardrail rules. Stub `ChatModel`/`EmbeddingModel` beans return canned responses.
2. **Integration tests:** Testcontainers (pgvector, Kafka), WireMock emulating the model API (including 429s, timeouts, malformed JSON) to test resilience and error paths.
3. **Tool/MCP contract tests:** tools called with model-like arguments (including invalid ones) behave safely.
4. **Evaluation suite (model in the loop):** golden set with thresholds (extraction field accuracy ≥ 97%, faithfulness ≥ 0.95, format validity 100%); a small smoke subset per PR, the full set nightly and before release; local models or the real provider in a test account.
5. **Safety suite:** prompt-injection and data-leak attempts must be blocked.
6. **Production checks:** canary rollout of prompt/model changes with online quality metrics.

**Trade-offs and what can go wrong**
- Real model calls in every unit test: slow, flaky, costly.
- Thresholds too tight -> flaky; too loose -> regressions slip through. Calibrate with repeated runs.
- Golden sets go stale; refresh with production samples.

**How I'd monitor it**
Eval scores per commit, flaky-test rate, cost of eval runs, production quality after each release.

**Follow-ups to expect**
- *Snapshot tests for prompts?* -> Useful for the rendered prompt (deterministic), not for model output.
- *Testing streaming?* -> Stub a Flux of chunks; assert assembly, cancellation and error events.
- *Who owns the golden set?* -> Domain experts with engineers; versioned in git.

**60-second answer**
"I split deterministic from statistical. Everything around the model, prompt rendering, retrieval filters, tool authorisation, parsing, guardrails, gets ordinary unit tests with stubbed models, and integration tests use Testcontainers and WireMock to simulate the provider, including 429s and malformed JSON. Model behaviour is tested with evaluation suites and thresholds, a smoke subset per PR and the full set nightly, plus a safety suite of injection and leak attempts. Prompt and model changes then go out as canaries with online quality metrics."

### Q12 [architect] What responsible AI, privacy and compliance controls does a GenAI feature need?
tags: responsible-ai, privacy, gdpr, eu-ai-act, governance, compliance, profile-java-genai

**Start here: the concepts**
- **Privacy:** data minimisation, purpose limitation, lawful basis, retention, data subject rights (GDPR; India's DPDP Act; sector rules like PCI DSS for card data).
- **Provider terms:** data retention, use of your data for training, processing region.
- **EU AI Act:** risk-based obligations phased in from 2025 onward (transparency for chatbots and generated content, stricter duties for high-risk uses); check the current timelines for your use case.
- **Responsible AI:** fairness, transparency, human oversight, accountability.

**The live scenario (functional requirement)**
*FR: "Launch an AI assistant for a bank's credit-card customers in Europe and India that answers questions and helps dispute transactions."*

**What the interviewer is really checking**
Awareness that GenAI in regulated domains needs governance designed in, and concrete engineering controls.

**How I answer it**
1. **Use-case risk assessment** with legal, risk and security: an informational assistant is lower risk; anything influencing credit decisions is high risk with much stricter requirements.
2. **Transparency:** users are told they're talking to AI; easy escalation to a human; AI-generated content labelled where required.
3. **Data minimisation:** send the model only what's needed; **never card numbers** (PCI): tokenise/mask before prompts; redact PII at the gateway.
4. **Provider controls:** approved models only, zero/limited data retention agreements, in-region processing, no training on our data.
5. **Retention and rights:** conversation logs with defined retention, deletion on request, access logging; crypto-shredding where needed.
6. **Human oversight:** dispute submissions are prepared by the AI but confirmed by the customer and processed by existing systems/rules.
7. **Accountability:** documentation of the system (model card, data sources, evaluations), audit trails of answers and sources, incident process for harmful outputs.
8. **Fairness and quality:** evaluate across languages and customer segments; monitor complaint patterns.

**Trade-offs and what can go wrong**
- Over-redaction removes context the model needs; redact selectively and re-insert values after generation where possible.
- Regulations evolve; keep a compliance owner and review regularly.

**How I'd monitor it**
PII redaction events, escalation rates, complaint categories, evaluation scores per language/segment, retention job success, audit coverage.

**Follow-ups to expect**
- *Can we send customer data to a hosted model?* -> Only under approved contracts, regions and minimisation; classification decides.
- *Explainability?* -> Citations and logged sources for informational answers; LLMs shouldn't make credit decisions unexplained.
- *Who signs off a launch?* -> A cross-functional AI governance review: product, legal, risk, security, engineering.

**60-second answer**
"It starts with a risk assessment: an informational card assistant is far lower risk than anything touching credit decisions. Then controls: customers know it's AI and can always reach a human; the model gets only minimal data, and card numbers are masked or tokenised before any prompt; only approved models with no-training, limited-retention, in-region terms; logs with retention limits and deletion on request; disputes prepared by AI but confirmed by the customer and processed by existing systems. Everything is documented, evaluated across languages and segments, and audited."
