---
id: genai-agents-mcp-deep-dive
title: Agentic AI in depth: the agent loop, planning patterns, tools, memory, MCP features, A2A, skills, graphs, human in the loop
stack: java
skill: genai
---
Part of the **reported interview questions** pack (hub: `../reported-interviews/README.md`). It covers the "Agentic AI
Complete Developer Study Notes" (sections 1-8 of the shared pages), the agent, MCP, A2A, graph and Embabel recipes in
Craig Walls' Spring AI Recipes, and the 25-repos PDF's themes. It goes deeper than bank 78, which holds the core answers.

**MCP facts are as of the 2026-07-28 specification**, which made the protocol stateless and deprecated roots, sampling and
logging. Spring AI 2.0's MCP annotations and many tutorials still show the earlier features, so **know both** and check
which protocol version your SDK supports. Community tools named here (`TaskTool`, `TodoWriteTool`, SkillsJars) come from
recipe titles, and I couldn't read the recipe articles themselves, so confirm names against current docs before quoting them.

### Q1 [fresher] What is agentic AI? How is an agent different from a chatbot? What are the levels of autonomy?
tags: agentic-ai, chatbot-vs-agent, autonomy-levels, agent-loop, agents, reported-genai

**Start here: the concepts**
- An **agent** works toward a **goal** and decides its own next steps: an LLM to reason, tools to act, memory for context, in a loop.
- **Agent = LLM + Tools + Memory + Loop.**

**The live scenario (functional requirement)**
*FR: "Build last month's sales report."* A chatbot explains how to do that. An agent queries the data, compares it with the prior month, makes a chart, writes the summary, and asks for help if it gets stuck.

**What the interviewer is really checking**
Clear definitions, and that you know more autonomy brings more risk.

**How I answer it** (120-second answer, point by point)

| Aspect | Chatbot | AI agent |
|---|---|---|
| Input | A question | A goal or task |
| Output | Text reply | Completed task plus a summary |
| Steps | One reply | Many, chosen by itself |
| Tools | Rarely | APIs, SQL, code, files, web |
| State | Current chat | Memory across steps and sessions |

Levels of autonomy:

| Level | Name | Who decides |
|---|---|---|
| 0 | Prompt | You ask, the model answers, and you do the work |
| 1 | Assistant | The model suggests, and you act |
| 2 | Workflow | Steps fixed in code, and the LLM fills each one |
| 3 | Agent | The LLM chooses the steps and the tools |
| 4 | Autonomous | Long-running, checks its own work, rare human input |

Key point: **more autonomy means more power and more risk.** Choose the lowest level that solves the problem. Common uses are coding, data analysis, customer support, research, operations and productivity tasks.

**Trade-offs and what can go wrong**
- "Agent" is overused. A fixed pipeline with one LLM call isn't an agent, and that's often a good thing.
- Level 4 needs strong guardrails, budgets and audit trails, and most production systems sit at levels 2 and 3.

**Follow-ups to expect**
- *How do you decide the level?* -> Q3.
- *More?* -> Bank 78 Q5.

**60-second answer**
"An agent works toward a goal and decides its own steps, using an LLM to reason, tools to act, and memory for context, in a loop. A chatbot replies; an agent does the work. There's a scale of autonomy, from a plain prompt, through an assistant that suggests, a workflow with fixed steps, and an agent that chooses steps, up to a long-running autonomous system. More autonomy means more power and more risk, so I pick the lowest level that solves the problem."

### Q2 [mid] What is inside an agent? Write the loop, and say when it should stop.
tags: agent-anatomy, agent-loop, pseudocode, stop-conditions, guardrails, max-steps, budget, reported-genai

**Start here: the concepts**
- Six parts: **model** (the brain), **instructions** (system prompt), **tools** (the hands), **memory** (the notebook), **orchestration** (the loop), and **guardrails** (the limits).
- The loop is what makes it an agent: **Think -> Act -> Observe**, repeated.

**The live scenario (functional requirement)**
*FR: "Find the top 5 products."* A bug makes a tool return an error that the model keeps retrying. With no step limit, it loops overnight, and the morning bill is large.

**What the interviewer is really checking**
Whether you can write the loop, and treat stopping as a design requirement.

**How I answer it** (120-second answer, point by point)

```text
context = [system_prompt, user_goal]
steps = 0
while steps < MAX_STEPS:
    reply = llm(context, tools)
    if reply.tool_call:
        result = run_tool(reply.tool_call)      # your code runs it
        context += [reply, result]
        steps += 1
    else:
        return reply.answer
return "Stopped: step limit reached"
```

Stop conditions, and all should exist:
1. It has a final answer.
2. The maximum number of steps or time is reached.
3. The token or money budget is used up.
4. An error needs a human to decide.
5. A guardrail blocks the next action.

What I'd add for production:
- **Loop detection:** the same tool with the same arguments repeated is a stuck agent.
- **Persist each step,** so a crash can resume and everything can be audited.
- **Timeouts per tool** and in total.
- **A partial result on stop,** so that the user gets something useful rather than only an error.

**Good agent qualities** are: reliable (similar result every time), transparent (shows its steps and sources), safe (only the access it needs) and efficient (few steps, low cost).

**Trade-offs and what can go wrong**
- A limit that's too low stops good runs. Set it from real step-count data.
- A tool's error message is fed to the model, so make it actionable: "month must be YYYY-MM" lets it self-correct.

**How I'd monitor it**
Steps per run, stop reason distribution, cost per run, tool error rate, and stuck-loop detections.

**Follow-ups to expect**
- *How does Spring AI do it?* -> `ChatClient` with tools runs the loop for you, through `ToolCallingAdvisor`. Add a limit and budget around it.

**60-second answer**
"An agent has six parts: the model, instructions, tools, memory, the orchestration loop, and guardrails. The loop is simple: call the LLM with context and tools; if it asks for a tool, my code runs it and appends the result; otherwise return the answer. The important part is stopping. It stops on a final answer, on a step or time limit, a token budget, an error needing a human, or a guardrail block. I also detect repeated identical calls, persist each step for resume and audit, and return partial results when it stops early."

### Q3 [senior] Workflow or agent: how do you decide? How do you test each?
tags: workflow-vs-agent, simplest-solution, determinism, testing, cost, reported-genai

**Start here: the concepts**
- **Workflow:** the steps are written in code. Predictable, cheaper and easy to test.
- **Agent:** the LLM decides the path at run time. Flexible, and harder to test.
- **Golden rule:** start with the simplest option that solves the problem, and add autonomy only when needed.

**The live scenario (functional requirement)**
*FR: "Process refund requests."* The steps are known: read the request, check the policy, check the order, decide, notify. An agent would add cost and variation for no benefit, so this should be a workflow.

**What the interviewer is really checking**
Restraint. Many candidates reach straight for agents.

**How I answer it** (120-second answer, point by point)

| Question | Workflow if | Agent if |
|---|---|---|
| Are the steps known in advance? | Yes | No, they depend on what's found |
| How many branches? | Few and enumerable | Too many to code |
| Cost of a wrong step? | High | Low, or a human reviews |
| Latency budget? | Tight | Flexible |
| Must results be repeatable? | Yes (audit) | Variation is acceptable |

1. **Start as a workflow:** an LLM fills steps inside a fixed flow, such as chaining, routing or parallel steps.
2. **Add one agentic step** only where it's needed, such as a research step in a known pipeline. This hybrid is often the best design.
3. **Move up with evidence:** when you see too many branches, or a growing pile of edge cases.

Testing:
| Type | Workflow | Agent |
|---|---|---|
| Unit | Each step, with mocked LLM | Each tool |
| Path | Assert the sequence | Assert end state, and permissions, not the exact path |
| Eval | Golden outputs | Task success rate over many runs, as a statistic |
| Limits | Timeouts | Step limits, budget, stuck-loop handling |

**Trade-offs and what can go wrong**
- A workflow with too many branches becomes a hard-to-maintain rule engine, which is the point at which an agent starts earning its cost.
- An agent's total cost and latency are unbounded unless you bound them.

**Follow-ups to expect**
- *What do graph frameworks add?* -> Q11. They let you mix fixed flow and agent steps.

**60-second answer**
"I start with the simplest thing that works. If steps are known in advance, the cost of a wrong step is high, or results must be repeatable, it's a workflow, with steps in code and the LLM filling them in. An agent earns its place when the path truly depends on what's found, and the branches are too many to code. Often the best design is a hybrid: a fixed pipeline with one agentic step. Testing differs too: a workflow asserts the path, and an agent asserts end state and permissions, and measures task success over many runs."

### Q4 [senior] Explain the planning patterns: chain-of-thought, ReAct, plan-and-execute, reflection, routing. When do you use which?
tags: react, plan-and-execute, reflection, chain-of-thought, tree-of-thoughts, routing, planning-patterns, reported-genai

**Start here: the concepts**
- Big goals must be broken into small, ordered steps. A plan keeps the agent focused, and re-planning lets it recover when a step fails.

**The live scenario (functional requirement)**
*FR: "Did revenue grow last month?"* A ReAct agent runs: Thought "need last month's revenue". Action `run_sql(...'2026-09')`. Observation 1,240,000. Thought "get the month before". Action `run_sql(...'2026-08')`. Observation 1,100,000. Answer "Revenue grew 12.7%". (1,240,000 / 1,100,000 = 1.127, so the figure checks out.)

**What the interviewer is really checking**
The differences, when to use each, and how to combine them.

**How I answer it** (120-second answer, point by point)

| Pattern | How | Best for | Weakness |
|---|---|---|---|
| Chain-of-thought | Reason step by step, then answer | Logic with no tools | Can reason wrongly, with confidence |
| **ReAct** | Think, call a tool, observe, repeat | Quick questions on live data | Can wander; costs grow per step |
| **Plan-and-execute** | Planner writes all the steps; executor runs them; re-plan on failure | Long, multi-part tasks | A rigid plan goes stale; costs extra planning |
| **Reflection** | Draft, critique, improve | When quality matters most | More calls; the critic can be wrong |
| Tree of thoughts | Explore several paths, and keep the best | Puzzles, search problems | Expensive |
| **Routing** | Send each task to the right model or agent | Many task types | Needs a good classifier |

1. **ReAct** is the most common agent pattern. Most frameworks' tool loops are effectively ReAct.
2. **Plan-and-execute:** "Monthly sales review" becomes get data, compare, chart, summary. A failed step goes back to the planner. A small model can run the executor, and a strong one can plan, which saves money.
3. **Reflection:** a second model or a checklist as the critic works better than self-review alone. Cap the rounds, usually at one or two.
4. **Combine them in real systems:** route to a specialist, plan, execute using ReAct, and reflect on the final output.
5. **A note on Chain-of-Thought:** reasoning models do this internally, so explicitly asking them for it may add nothing.

**Trade-offs and what can go wrong**
- Each pattern adds model calls. Reflection on every message can double the cost.
- Stated reasoning isn't guaranteed to match why a model did something, so don't treat it as audit evidence.

**How I'd monitor it**
Steps per pattern, re-plan rate, the quality gain from reflection against its cost, and routing accuracy.

**Follow-ups to expect**
- *Goal-oriented planning?* -> Q12: Embabel's GOAP plans in code, without the LLM picking the path.

**60-second answer**
"ReAct is the most common: think, call a tool, observe, repeat. It's good for quick questions on live data. Plan-and-execute writes the full plan first, then executes, re-planning on failure, which suits long multi-part tasks, and a cheap model can execute. Reflection drafts, critiques, then improves when quality matters most, and a second model or a checklist makes a better critic. Routing sends each task to the right model or agent. Real systems combine them: route, plan, execute with ReAct, and reflect at the end, while capping the extra calls, since every pattern adds cost."

### Q5 [senior] How do you design good tools for an agent? How do you make tool use efficient?
tags: tool-design, function-calling, tool-selection, parallel-tools, json-schema, efficient-tool-use, reported-genai

**Start here: the concepts**
- A **tool** is a function an agent may call, with a name, a description and an input schema.
- The **description tells the LLM when to use it**, so it counts as much as the code.
- **The LLM only decides. Your code executes.**

**The live scenario (functional requirement)**
*FR: "Sales agent with database access."* A tool called `tool1` with no description gets called wrongly. A `run_any_sql` tool returns 10,000 rows, which floods the context, and a prompt injection could make it run a `DELETE`.

**What the interviewer is really checking**
Practical tool design, and the security side of giving an LLM access to systems.

**How I answer it** (120-second answer, point by point)

```java
@Tool(description = "Total sales for a region and month. Month format is YYYY-MM.")
SalesTotal getSales(@ToolParam(description = "Region name, e.g. North") String region,
                    @ToolParam(description = "Month as YYYY-MM") String month) { ... }
```

Design rules:
1. **Clear names:** `get_sales`, not `tool1`.
2. **One job per tool,** with small, typed inputs.
3. **Short, focused results:** the top rows and key fields, not 10,000 rows.
4. **Helpful errors the LLM can act on:** "month must be YYYY-MM".
5. **Separate read tools from write tools,** and give each agent only what it needs.
6. **Ask for confirmation before risky actions.**
7. **Idempotent writes,** since a tool can get called twice.
8. **Treat arguments as untrusted input:** validate them, parameterise SQL, and enforce the user's permissions in code, not in the prompt.

Calling patterns: **single** (today's exchange rate), **sequential** (find customer, then get orders), and **parallel** (sales for 4 regions at once).

Making tool use efficient:

| Problem | Fix |
|---|---|
| Too many tool definitions fill the context | Load tools on demand by searching a tool catalogue, or limit by task |
| Wrong tool chosen | Better descriptions, fewer overlapping tools, and test tool selection |
| Slow step by step calls | Parallel calls where the steps are independent |
| Large results | Summarise, paginate, or store the result and return a reference |

**Trade-offs and what can go wrong**
- Tool definitions cost tokens on every call, and 50 tools can use a big share of the context.
- Overlapping tools confuse selection. Merge them, or route first.
- Tool output is untrusted, and it can contain injected instructions.

**How I'd monitor it**
Calls per tool, tool error rate, wrong-tool rate on an eval set, result sizes, and tokens used by definitions.

**Follow-ups to expect**
- *Which tools are common?* -> Web search, SQL, sandboxed code execution, files, business APIs, browser.
- *Basics?* -> Bank 78 Q1.

**60-second answer**
"A tool has a name, a description and a schema, and the description is what tells the LLM when to use it, so I treat it as a prompt. Each tool has one job with small typed inputs, returns focused results rather than thousands of rows, and gives errors the model can act on. I separate read and write tools, ask for confirmation on risky actions, and make writes idempotent. The model only decides and my code executes, so arguments are untrusted: validate them, parameterise SQL, and enforce the user's permissions in code. Too many tool definitions hurt too, so I load them on demand."

### Q6 [mid] What types of memory does an agent need? What should it store, and what shouldn't it?
tags: agent-memory, short-term, long-term, scratchpad, episodic, procedural, vector-store, reported-genai

**Start here: the concepts**
- LLMs forget everything between calls. **Short-term** memory covers the current task; **long-term** memory covers across tasks.

**The live scenario (functional requirement)**
*FR: "A monthly reporting agent."* It should remember that the target margin is 25% and that May's report failed because of missing data, and it should never store the database password it saw in a config file.

**What the interviewer is really checking**
A concrete design, including what not to keep.

**How I answer it** (120-second answer, point by point)

| Type | Holds | Example |
|---|---|---|
| Short-term | Current conversation | Last 10 messages |
| Long-term | Facts across sessions | "User prefers Power BI" |
| Episodic | Past runs and events | "May report failed: missing data" |
| Semantic | Knowledge and definitions | Company KPI formulas |
| Procedural | How to do tasks | Steps for the monthly report |

**Keeping short-term memory small:** a sliding window, summarising old turns, storing key fields rather than full tool results, and a **scratchpad**: a notes file the agent updates as it works.

**Long-term flow:** important fact -> embedding model -> vector database (pgvector, Qdrant, Chroma) -> similarity search on a new question -> added to the context.

| Store | Avoid |
|---|---|
| User preferences | Passwords and API keys |
| Decisions and outcomes | Raw personal data |
| Definitions and rules | Data that changes daily |
| Lessons from errors | Everything "just in case" |

**Good practices:** give each memory a date and a source; let users view and delete what's saved; and update or remove facts when they change.

**Trade-offs and what can go wrong**
- A vector store retrieves by similarity, so an old contradicted fact can come back. Keep timestamps, and prefer recent ones.
- **Memory poisoning:** a malicious document can plant false facts that persist across sessions.
- Agents that write their own memory need review or limits on what they can store.

**Follow-ups to expect**
- *In Spring AI?* -> Bank 66 Q6.
- *Concepts?* -> Bank 69 Q11.

**60-second answer**
"Short-term memory covers the current task, and long-term covers across tasks, including facts, past runs and procedures. To stay within the context window, I use a sliding window, summaries, trimmed tool results, and a scratchpad file. Long-term facts are embedded into a vector store and retrieved by similarity. I store preferences, decisions, definitions and lessons from errors. I never store passwords, keys or raw personal data. Each memory gets a date and source, users can see and delete them, and I watch for stale or poisoned memories."

### Q7 [senior] Beyond tools: what can MCP do? Explain prompts, completions, progress, elicitation, sampling, logging, and what changed in the 2026-07-28 spec.
tags: mcp, sampling, elicitation, progress, prompts, completions, stateless, mrtr, streamable-http, stdio, spring-ai, reported-genai

**Start here: the concepts**
- **MCP** is an open standard for connecting AI apps to tools and data: "USB-C for AI". Build a server once, and any MCP-compatible app can use it.
- **Host -> client -> server -> system.** The host is the AI app, with one client per server.
- A server exposes **tools** (the model can call), **resources** (data the app can read), and **prompts** (reusable templates).

**The live scenario (functional requirement)**
*FR: "An MCP server for a booking system, used from an IDE and a company chat app."* A booking tool needs a missing detail from the user, a long search should show progress, and users should get a menu of ready-made prompts.

**What the interviewer is really checking**
Depth beyond tools, and whether you're current. Many tutorials still describe pre-2026 behaviour.

**How I answer it** (120-second answer, point by point)

| Feature | Direction | What it does | Spring AI annotation (2.0) |
|---|---|---|---|
| Tools | Client to server | Actions the model can call | `@McpTool` |
| Resources | Client to server | Readable data | `@McpResource` |
| Prompts | Client to server | Reusable templates, often user-triggered | `@McpPrompt` |
| Completions | Client to server | Autocomplete for prompt arguments | `@McpComplete` |
| Progress | Server to client | "40% done" on long operations | `@McpProgress` |
| Logging | Server to client | Sends logs to the client | `@McpLogging` |
| Elicitation | Server asks the user | Asks for a missing detail mid-tool | `@McpElicitation` |
| Sampling | Server asks the client's LLM | Server uses the model without its own key | `@McpSampling` |

**Transports:** stdio for local servers on your computer, and Streamable HTTP for remote servers. In Spring AI: `spring.ai.mcp.server.protocol=STREAMABLE` or `STATELESS`, or `spring.ai.mcp.server.stdio=true`.

What changed in the 2026-07-28 specification:
1. **Stateless:** the `initialize` handshake and protocol-level sessions were removed, so each request stands alone. Scaling behind a load balancer becomes much simpler.
2. **Elicitation and sampling changed form:** the old server-initiated requests depended on session state. They're replaced by **Multi Round-Trip Requests**: a result with an `input_required` status asks the client for more input, and the client calls again.
3. **Roots, sampling and logging are deprecated.**
4. **Check compatibility:** servers on the new revision may not work with older clients, and vice versa. Spring AI's docs don't name a protocol revision, so check the MCP Java SDK.

**In an interview, say this directly:** "Elicitation and sampling exist in most tutorials and in Spring AI 2.0's annotations. The latest spec reworks them, so I'd check which revision my SDK targets."

**Trade-offs and what can go wrong**
- Sampling let a server trigger model calls using the client's budget, which was a real concern even before its deprecation.
- Don't ask for secrets through elicitation in a form the host may log.
- MCP standardises the connection. It doesn't solve security or tool quality for you (Q8).

**How I'd monitor it**
Per-tool latency and errors, auth failures, and protocol version distribution among clients.

**Follow-ups to expect**
- *Bank 78 Q2 and Q3* cover the basics and building a server.
- *How do you try it quickly?* -> JBang can run a small MCP server as a single file.
- *What's MCP Apps?* -> Q13.

**60-second answer**
"Beyond tools, MCP has resources, prompts, argument completions and progress. Elicitation lets a tool ask the user for a missing detail, and sampling lets a server use the client's model. But be careful, because the July 2026 spec changed a lot. It's now stateless, with no initialize handshake and no sessions, which makes horizontal scaling simple. Elicitation and sampling's old server-initiated forms are replaced by multi-round-trip requests, and roots, sampling and logging are deprecated. Spring AI 2.0 still has annotations for those, so I'd check which protocol revision my SDK targets, especially since old and new can be incompatible."

### Q8 [architect] How do you secure an MCP server? API key vs OAuth, and controlling tool visibility.
tags: mcp-security, oauth2, api-key, tool-visibility, tool-poisoning, least-privilege, confused-deputy, reported-genai

**Start here: the concepts**
- A remote MCP server is an API that an LLM can reach, so it needs all normal API security, and more.
- **Tool visibility:** different callers see different tools.

**The live scenario (functional requirement)**
*FR: "An HR MCP server."* Everyone can search the holiday calendar. Only HR can see `update_salary`. An injected instruction in a document must not be able to change anyone's salary.

**What the interviewer is really checking**
That you understand the trade-off between methods, and the risks specific to agents.

**How I answer it** (120-second answer, point by point)

| Method | Good for | Limit |
|---|---|---|
| stdio (no network) | Local tools | Runs with the user's permissions, so vet what you install |
| API key | Internal or simple service access | Identifies an app, not a user; rotation and leaks |
| OAuth 2.1 | Remote servers with real users | More setup, and it gives per-user, scoped access |

1. **OAuth for remote servers:** the MCP server is a **resource server** that verifies tokens. With Spring Security, it's standard resource server configuration: check `aud`, so that a token meant for another service gets rejected.
2. **Tool visibility:** filter the tool list by the caller's role and scopes, so a user doesn't even see `update_salary`. **Also enforce on the call**, because hiding isn't authorization.
3. **Don't pass tokens through:** a server shouldn't forward the client's token to downstream APIs. Use its own, or token exchange. Otherwise you have a confused-deputy problem.
4. **Agent-specific risks:**

| Risk | Control |
|---|---|
| Tool poisoning, in which a description carries hidden instructions | Allow-list servers, review descriptions, pin versions |
| Prompt injection through tool results | Treat as data; approval for destructive tools |
| A "rug pull", when a server changes tools after approval | Alert on tool-definition changes |
| Too much access | Least privilege, per-tool scopes |
| Data exfiltration | Limit outbound calls; check tool combinations |

5. **Human approval** for anything destructive or financial, and **audit logs** for every call, with user, tool and arguments (masked).

**Trade-offs and what can go wrong**
- An API key shared across users means no per-user audit, and every call has the same permissions.
- Running community MCP servers locally is like running any downloaded code.

**How I'd monitor it**
Auth failures, denied tool calls, tool-definition changes, unusual tool sequences.

**Follow-ups to expect**
- *More?* -> Bank 78 Q4.

**60-second answer**
"An API key is fine for simple internal access, but it identifies the app rather than the user, so remote servers with real users should use OAuth 2.1, with the MCP server as a resource server that checks audience and scopes. I filter visible tools by role, and also enforce on each call, since hiding isn't authorization. I don't forward the user's token downstream. Then there are agent-specific risks: tool poisoning, injection through tool results, and tool definitions changing after approval. So I allow-list and pin servers, apply least privilege, require human approval for destructive tools, and audit every call."

### Q9 [senior] MCP vs A2A, and how do sub-agents fit? When is a multi-agent design justified?
tags: a2a, mcp-vs-a2a, agent-card, subagents, orchestrator, linux-foundation, multi-agent, reported-genai

**Start here: the concepts**
- **MCP:** agent to **tools and data**. Calling functions, reading data. Started by Anthropic.
- **A2A (Agent2Agent):** agent to **agent**. Sharing tasks and results. Started by Google, and donated to the Linux Foundation in June 2025.
- **Sub-agent:** a specialised agent with its own instructions, tools and clean context.

**The live scenario (functional requirement)**
*FR: "A research assistant reads 40 documents, and a procurement agent in another department must be consulted."* The 40 documents would flood one context, so a sub-agent reads them and returns a summary. The other department's agent runs on another team's platform, and that calls for A2A.

**What the interviewer is really checking**
That these protocols are complementary, and that you have a reason to go multi-agent.

**How I answer it** (120-second answer, point by point)

| | MCP | A2A |
|---|---|---|
| Connects | Agent to tools and data | Agent to agent |
| Discovery | List the server's tools | An **Agent Card** describing skills and endpoint |
| Unit of work | A tool call | A task, possibly long-running |
| Internals | Tool is a defined function | The other agent stays opaque |

1. **They're complementary:** an agent uses MCP for its tools, and A2A to reach other agents. The Linux Foundation hosts both.
2. **Sub-agents in the same process:** the orchestrator delegates, the sub-agent works in its own context, and it returns only a summary. This protects the main context from noise. That's context isolation, and is the main reason to use sub-agents. In Spring AI, recipe topics include Claude-style sub-agents, and invoking A2A agents through a task tool.
3. **Justified when:** there are separate teams or owners, different data permissions, different models for different tasks, a need for context isolation, or truly parallel work.
4. **Not justified when:** one agent with a few tools can do it. Multiple agents add latency, cost and more ways to fail.
5. **Design points:** clear contracts for each agent, a depth limit, a shared budget, and tracing across agents using one trace id.

**Trade-offs and what can go wrong**
- Passing a summary can drop details. Have sub-agents return structured results, plus references to full data.
- Each hand-off can lose or distort intent, the agent version of a game of telephone.
- A2A across organisations needs real authentication. Signed Agent Cards were reported in v1.0, so verify that against the spec.

**How I'd monitor it**
One trace per request, across agents; cost per agent; delegation depth; and failure rate per hand-off.

**Follow-ups to expect**
- *More?* -> Bank 78 Q6.

**60-second answer**
"MCP connects an agent to tools and data, and A2A connects agents to each other, with an Agent Card for discovery and tasks as the unit of work. They're complementary, and both now sit under the Linux Foundation. Sub-agents are specialists with their own clean context. The main benefit is isolation: one can read 40 documents and return a summary, without flooding the main context. I go multi-agent only for a real reason: separate owners, different permissions, or context isolation. Otherwise, one agent with a few tools is cheaper and more reliable. And I set a depth limit, a shared budget and one trace across all agents."

### Q10 [mid] What are agent skills, and how do you reuse agent behaviour? What is a planning tool?
tags: agent-skills, skillsjars, progressive-disclosure, todowrite, ask-user, procedural-memory, reported-genai

**Start here: the concepts**
- A **skill** is a packaged set of instructions, and sometimes scripts, that the agent loads **only when relevant**. It's procedural memory in a file.
- **Progressive disclosure:** the agent sees a short description up front, and reads the full content only when needed.
- A **planning tool** gives the agent a to-do list it can update, so that long tasks stay on track.

**The live scenario (functional requirement)**
*FR: "Our agents should all write release notes the same way."* Pasting those instructions into every system prompt costs tokens on each call, and they drift apart. A shared skill loads only when someone asks for release notes.

**What the interviewer is really checking**
Understanding why skills save context, and how you'd share them across teams.

**How I answer it** (120-second answer, point by point)
1. **Format:** a folder with a `SKILL.md` file that has a name and description, plus optional reference files and scripts.
2. **How it saves context:** only the name and description sit in the prompt. The agent reads the rest on demand, so 50 skills cost far less than 50 sets of instructions.
3. **The description is decisive,** as with tools, because it's how the agent decides whether to load it.
4. **Sharing:** version in Git; in the JVM world, a recipe topic packages skills as JARs (SkillsJars), which fits normal dependency management.
5. **Skills vs tools vs MCP:** a tool **does** something; a skill **teaches how**; MCP **connects** to systems. A skill often tells an agent how to use certain tools well.
6. **Planning tool:** a `TodoWrite`-style tool has the agent write its steps, mark them as done and revise them. It helps the agent avoid forgetting steps, and it shows the user what's happening.
7. **Asking the user:** an "ask a question" tool lets the agent stop and clarify, rather than guessing. It's a simple and valuable form of human-in-the-loop.

**Trade-offs and what can go wrong**
- A skill with scripts is **running code**. Vet third-party skills like any dependency, since they may contain malicious instructions.
- Vague descriptions mean the skill either never loads, or loads too often.
- Test that it triggers when it should, and evaluate its effect.

**Follow-ups to expect**
- *How is that different from RAG?* -> RAG retrieves facts by similarity; a skill supplies a procedure the agent chooses to load.

**60-second answer**
"A skill is packaged instructions, sometimes with scripts, that an agent loads only when relevant. Only its name and description sit in the prompt, so you can have many without filling the context. It's procedural memory in a file, versioned in Git or shipped as a JAR in the JVM world. A tool does something, a skill teaches how, and MCP connects to systems. A planning tool gives the agent a to-do list to update, which keeps long tasks on track. And I vet third-party skills like any dependency, since they can run code."

### Q11 [senior] How do graph-based agent workflows work? Loops and human-in-the-loop with LangGraph4j or Spring AI Alibaba.
tags: langgraph4j, spring-ai-alibaba, graph-workflow, state, checkpoint, human-in-the-loop, conditional-edge, reported-genai

**Start here: the concepts**
- A **graph workflow** models the process as **nodes** (steps), **edges** (what's next), and shared **state**. Conditional edges and loops are allowed.
- A **checkpoint** saves state, so a run can pause and resume.
- **Human-in-the-loop (HITL)** means pausing until a person approves.

**The live scenario (functional requirement)**
*FR: "Draft a contract clause, review it, loop until acceptable or 3 tries, then pause for legal approval, which may take 2 days."* A plain loop can't sit for 2 days across a server restart.

**What the interviewer is really checking**
Why graphs help: they make control explicit, and they make pauses durable.

**How I answer it** (120-second answer, point by point)

```text
START -> draft -> review --(good)--> legal_approval (pause) --(approved)--> publish -> END
           ^        |                                       --(rejected)--> draft
           +--(needs work, tries < 3)--+
                    +--(tries >= 3)--> escalate -> END
```

1. **Nodes** are functions: an LLM call, a tool, or plain code.
2. **State** is a typed object that each node reads and updates. Keep it small and serialisable.
3. **Conditional edges** choose the next node from state. The model can influence the path, while your code keeps control over which paths exist.
4. **Loops** need an exit: a counter in state is required, or you get an infinite loop.
5. **Human in the loop:** at `legal_approval`, the graph saves a checkpoint and stops. No thread waits. When the person approves, an API call loads the checkpoint and resumes. This survives restarts when the checkpoint store is a database.
6. **Libraries:** LangGraph4j and Spring AI Alibaba Graph, and the latter has visualisation support, useful for reviewing a flow.

**Trade-offs and what can go wrong**
- Don't use a graph for a straight line of steps. It's a heavy way to write three method calls.
- Compared with a pure agent: more predictable and testable, and less flexible.
- Changing the graph while old runs are paused needs versioning of the state and the definition, as with any workflow engine.
- Resuming must not repeat side effects, so make nodes idempotent.

**How I'd monitor it**
Node durations, loop counts, the number of pauses and how long they last, and failed resumes.

**Follow-ups to expect**
- *Why not Temporal or Camunda?* -> They're a good fit for durable business processes with AI steps inside. Agent graphs add LLM-specific conveniences. For long, critical workflows, I'd seriously consider a workflow engine.

**60-second answer**
"A graph workflow makes control explicit: nodes are steps, edges say what comes next, and shared state carries the data, with conditional edges and loops. The LLM can influence the path, but only paths I defined exist. Loops need a counter so they exit. For human approval, the graph checkpoints state to a database and stops, with no thread waiting, and an API call later resumes it, even days later and across restarts. LangGraph4j and Spring AI Alibaba Graph do this on the JVM. I use graphs when there's branching and pausing, and I make nodes idempotent because resuming can repeat work."

### Q12 [senior] What is Embabel, and how does it differ from LLM-driven agents?
tags: embabel, goap, goal-oriented-action-planning, rod-johnson, typed-agents, jvm, reported-genai

**Start here: the concepts**
- **Embabel** is a JVM agent framework from Spring's creator, Rod Johnson, launched in 2025, built on Spring.
- It plans with **GOAP (Goal-Oriented Action Planning)**, a pathfinding algorithm that doesn't use an LLM and is known from games.

**The live scenario (functional requirement)**
*FR: "An insurance claim agent must only use approved steps."* In a free-form agent, the model chooses its next step, so an unapproved path is possible. With GOAP, the planner can only combine actions you've defined.

**What the interviewer is really checking**
Whether you know the JVM landscape, and the idea of separating planning from LLM calls.

**How I answer it** (120-second answer, point by point)
1. **Actions are typed Java or Kotlin methods** with preconditions and effects, such as: "needs a `Claim`, and produces an `Assessment`".
2. **A goal** is the state you want, such as having a `Decision`.
3. **The planner** finds a path of actions from the current state to the goal. It's deterministic, and it can only use actions that exist.
4. **LLM calls happen inside actions,** for a specific job, so the model does the fuzzy work and code controls the flow.
5. **Re-planning:** after each action, it can change path as conditions change.
6. **Typed state** on the blackboard means the compiler helps you. Human-in-the-loop can be added as a step that waits for input.

| | LLM-driven agent | Embabel GOAP |
|---|---|---|
| Who picks the next step | The model | A deterministic planner |
| Allowed paths | Whatever the model decides | Only defined actions |
| Explainability | Harder | The plan can be inspected |
| Flexibility for the unforeseen | High | Limited to known actions |
| Effort | Lower to start | Model the actions up front |

**Trade-offs and what can go wrong**
- If an action isn't defined, the planner can't invent it, which is the point, and also the limit.
- It's younger than the mainstream frameworks. Check its maturity and community for your needs.

**Follow-ups to expect**
- *Spring AI's own agentic support?* -> The team planned to release agentic support in November 2026 as an experimental separate project, merging into Spring AI 3.0. Check the current status.

**60-second answer**
"Embabel is a JVM agent framework from Rod Johnson. Rather than the LLM choosing each step, it uses goal-oriented action planning: you write typed actions with preconditions and effects, you state a goal, and a deterministic planner finds a path, re-planning as things change. LLM calls happen inside actions for the fuzzy work. So code controls the flow and only approved paths are possible, which is attractive in regulated domains. The trade-off is less flexibility, since it can't invent an action you didn't define."

### Q13 [mid] How do you build a user interface for an agent? AG-UI, CopilotKit and MCP Apps.
tags: ag-ui, copilotkit, mcp-apps, streaming, agent-ui, sse, generative-ui, reported-genai

**Start here: the concepts**
- A chat box isn't enough when an agent takes many steps. The UI needs to show progress, tool calls and approvals.
- **AG-UI** is a protocol for streaming agent events to a front end. **CopilotKit** is a front-end toolkit that uses it.
- **MCP Apps** lets an MCP server return an interactive UI, not just text.

**The live scenario (functional requirement)**
*FR: "A travel agent shows flight options as cards, the user clicks one, and the agent continues."* Text-only replies force the user to type "the second one".

**What the interviewer is really checking**
Awareness that agents change UX, and the trust issue with UI supplied by a server.

**How I answer it** (120-second answer, point by point)
1. **What to stream:** run started, step started, tool call, partial text, state update, an approval needed, and finished. Users trust an agent more when they can see what it's doing.
2. **Transport:** Server-Sent Events usually suffice for server-to-client streaming, and a POST sends user actions back. WebSocket if it's truly two-way (bank 98 Q15).
3. **Human-in-the-loop in the UI:** clear approve or reject buttons, showing exactly what will happen. Also a stop button.
4. **MCP Apps:** a tool result refers to UI that the host renders in a sandbox, and interactions flow back to the agent. So the same server gives a rich experience in any supporting host.
5. **In Spring:** a recipe topic covers exposing a Spring AI agent via AG-UI to CopilotKit, including rendering MCP Apps UIs there.

**Trade-offs and what can go wrong**
- **Server-supplied UI is untrusted code.** It must be sandboxed, and shouldn't reach the host's cookies or data.
- These standards are moving quickly, so wrap them, and don't let them spread through your codebase.
- Don't show raw reasoning as a guarantee of why the agent did something.

**Follow-ups to expect**
- *What happens on a dropped connection?* -> Event ids and resume, or poll job status, because agent runs outlast connections.

**60-second answer**
"A long-running agent needs more than a chat box. I stream events: steps started, tool calls, partial text, and approvals needed, usually over SSE, and include a clear stop button and approve or reject with exactly what will happen. AG-UI standardises those events, and CopilotKit is a front-end toolkit that uses them. MCP Apps lets a server return interactive UI like flight cards, and the host renders it in a sandbox, since server-supplied UI is untrusted. These standards move fast, so I keep them behind a thin layer."

### Q14 [mid] Someone shows you a vendor's "agentic AI ecosystem" diagram. How do you explain the layers, and how do you evaluate it?
tags: agent-platform, managed-agents, agent-sdk, claude, ecosystem-diagram, vendor-evaluation, reported-genai

**Start here: the concepts**
- A viral diagram isn't documentation. Infographics mix real products with descriptions the author made up, and go out of date fast.

**The live scenario (functional requirement)**
A widely shared "Anthropic Claude Agentic AI Ecosystem" infographic lists models, frameworks, workspace products, memory, security and deployment layers. An interviewer asks what you'd take from it.

**What the interviewer is really checking**
Whether you can separate general layers from vendor marketing, and verify before repeating.

**How I answer it** (120-second answer, point by point)
1. **The general layers are useful, whichever vendor it is:**

| Layer | Question it answers |
|---|---|
| Models | Which one, at what cost and speed? |
| Framework and tools | How do I build the loop and connect tools? |
| Hosted or self-hosted runtime | Who operates state, sandboxes and scaling? |
| Memory and storage | What persists, and who controls it? |
| Security and governance | Who may do what, and what's the audit trail? |
| Evaluation and improvement | How do I know that it works? |

2. **Verify against official docs.** For this example, I checked official Anthropic pages:

| Claim | Status |
|---|---|
| Claude Agent SDK runs self-hosted agents | Confirmed: runs on your machines, in Python and TypeScript |
| Claude Managed Agents is hosted | Confirmed: hosted harness with state, memory, permissions |
| Cowork exists, with memory | Confirmed |
| Memory stores | Confirmed, in beta for Managed Agents |
| Specific model versions | Out of date quickly; check the current model list |
| "Constitutional AI Checker", "RLHF Compliance Engine" as customer-facing products | I found no official product with these names; treat as the author's labels |

3. **The buy-or-build decision is the real interview question:** self-hosted SDK for control and data residency, and a managed runtime for speed to production. Compare data handling, lock-in, cost and portability.
4. **Stay vendor-neutral:** the same layers exist on other platforms.

**Trade-offs and what can go wrong**
- Quoting a diagram's product names or benchmark claims as fact is an easy way to lose credibility.
- A managed runtime reduces work, and increases dependence on one vendor.

**Follow-ups to expect**
- *Reference architecture?* -> Bank 78 Q10.

**60-second answer**
"I treat diagrams like that as a map of layers, not as documentation. The useful layers apply to any vendor: models, framework, runtime, memory, security, evaluation. Then I verify names against official docs. For that Claude one, the Agent SDK, Managed Agents and Cowork are real, while labels like a 'compliance engine' didn't match any official product I could find, and model versions date quickly. The real decision it raises is self-hosted versus managed runtime: control and portability against speed to production."

### Q15 [architect] What are the next areas to watch: GraphRAG with Neo4j and advanced autonomous agents?
tags: graphrag, neo4j, agentic-graphrag, autonomous-agents, knowledge-graph, sandboxing, reported-genai

**Start here: the concepts**
- **GraphRAG** retrieves through a **knowledge graph** of entities and relationships, rather than just similar chunks.
- **Autonomous agents** run for long periods with little human input.

**The live scenario (functional requirement)**
*FR: "Which suppliers are affected if this factory closes, and which of our contracts depend on them?"* That answer needs following relationships across many documents, and similarity search alone won't assemble it.

**What the interviewer is really checking**
That you know when each one is worth its cost, rather than only that it exists.

**How I answer it** (120-second answer, point by point)
1. **Vector RAG's weak spot:** multi-hop and "across the whole dataset" questions, since the answer isn't in any single chunk.
2. **GraphRAG build:** an LLM extracts entities and relationships into a graph like Neo4j, with embeddings on nodes. Query time combines vector search to find a starting point, with graph traversal to expand.
3. **Agentic GraphRAG:** the agent chooses between tools, such as vector search, a Cypher query, or both, and checks the results.
4. **Cost:** extraction across all documents takes LLM calls, extracted entities can be wrong, and the graph must be kept up to date. Choose it for genuinely connected data, like supply chains, fraud rings and compliance.
5. **Advanced autonomous agents need:**

| Need | Why |
|---|---|
| Durable state and resume | Runs can outlast processes |
| Sandboxed execution | They run code and browse |
| Budgets and kill switches | Costs and mistakes compound |
| Self-checking | Verify with tests, not just self-assessment |
| Full audit trail | Accountability for actions |
| Approval gates for risky actions | Blast-radius control |

6. **Spring AI's roadmap:** agentic support planned as a separate experimental project, then merged in 3.0. Treat it as "watch this".

**Trade-offs and what can go wrong**
- Don't start with a graph because it's fashionable. Run a baseline with hybrid RAG first, and see what fails.
- Graph queries generated by an LLM need safeguards, such as read-only access, like any generated SQL.

**How I'd monitor it**
Answer quality on multi-hop test questions against the baseline, and for autonomy: task success, human interventions, cost per task, and policy violations.

**Follow-ups to expect**
- *Which learning resources?* -> The hub lists the 25 repos from the PDF, by level.

**60-second answer**
"Vector RAG struggles with multi-hop questions, because the answer isn't in one chunk. GraphRAG extracts entities and relationships into something like Neo4j, then uses vector search to find a starting point and traversal to expand. That suits connected data such as supply chains or fraud, but extraction is costly, can be wrong, and must be maintained, so I'd baseline with hybrid RAG first. For autonomous agents, the hard part isn't the loop. It's durable state, sandboxing, budgets, kill switches, verification and audit. I'd give autonomy to low-risk work first."
