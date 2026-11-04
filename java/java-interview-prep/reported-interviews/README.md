# Reported interview questions and GenAI study pack

A starting point for any developer preparing for a Java backend or Java + GenAI interview. Questions that real candidates
posted, plus popular GenAI study material, are collected here, and each one is linked to a deep answer written in plain
language. Everything is also in the **Interview Coach**, so you can search it, drill it and run a mock interview.

## How to use this

1. **Find your target below.** Each section lists questions and the answer for each.
2. **Say the answer aloud.** Each new answer has a *60-second answer* for rapid-fire rounds, and a longer *How I answer it* for when they say "go deeper".
3. **Replace the examples with your own experience.** The scenarios are examples, so never claim an experience you don't have. Interviewers probe for details, and honest reasoning scores better than a borrowed story.
4. **Run the code.** Three programs check the code and many of the claims in these answers.

```bash
cd java/java-interview-prep/examples/21_coding_interview
java 07_streams_sde2_employee_drills.java                # 35 streams questions, ties and null cases included
java 08_reported_rounds_coding_and_internals.java        # coins, nearest pair, proxies, parallel Collector, locks
java 09_vector_search_and_llm_sampling_from_scratch.java # cosine, ANN recall, chunking, RRF, temperature and top-p
```

**A warning about all of this material.** Interview reports are one person's experience and vary by team, level and
year. Treat them as likely topics, not a syllabus. Social-media infographics are often incomplete or simply wrong
([see the corrections below](#corrections-to-the-source-material)). Scenarios are illustrative, not from any named company.

## What's new

| Bank | Topic | Questions | Coach topic |
|---|---|---|---|
| [95](../interview-scenarios/95_reported_streams_coding.md) | Streams: 20 coding drills | 20 | Coding round |
| [96](../interview-scenarios/96_reported_streams_concepts.md) | Streams: 15 concepts | 15 | Java 8, 11 and modern Java |
| [97](../interview-scenarios/97_reported_core_java_senior.md) | Senior core Java: proxies, collectors, locks, concurrency failures | 9 | Java 8, 11 and modern Java |
| [98](../interview-scenarios/98_reported_spring_backend_rounds.md) | Spring backend: coding, JUnit, JPA keys, OAuth/JWT, rate limiter, Redis, WebSocket, SonarQube, discovery, Java 17, Boot 1-4 | 20 | Spring and Spring Boot |
| [99](../interview-scenarios/99_reported_api_design_patterns.md) | API design: 12 patterns, errors, lost updates | 3 | REST API |
| [88](../interview-scenarios/88_reported_database_rounds.md) | Databases: MVCC, cascade, locks, SQL vs NoSQL for money | 4 | SQL |
| [89](../interview-scenarios/89_reported_production_kafka_design.md) | Fraud platform, millions of events, hangs, pool exhaustion, Git, secrets in logs | 6 | System design |
| [69](../interview-scenarios/69_genai_fundamentals_40_concepts.md) | GenAI fundamentals: all 40 concepts | 12 | GenAI |
| [67](../interview-scenarios/67_genai_rag_vector_databases.md) | RAG and vector databases in depth | 14 | GenAI |
| [66](../interview-scenarios/66_genai_spring_ai_recipes.md) | Spring AI in practice | 12 | GenAI |
| [68](../interview-scenarios/68_genai_agents_mcp_deep_dive.md) | Agents, MCP features, A2A, skills, graphs | 15 | GenAI |
| [33](../interview-scenarios/33_aws_basics.md) | AWS basics: IAM, EC2, VPC, S3, Lambda, compute choices, load balancers, databases, messaging, monitoring, deployment, cost | 15 | Cloud, Docker and Kubernetes |
| **Total** | | **145** | |

Questions that the repo already answered well are linked rather than repeated. Tags let you search by source in the
coach: `reported-streams`, `reported-rounds`, `reported-genai`, or by company: `deloitte`, `mastercard`, `capgemini`, `virtusa`.

## Plans by experience

The coach's **Topics** tab opens with a picker: **2+ years**, **6+ years**, **Senior engineer** (10+, hands-on) or **Architect or lead** (12+).
Each builds a short plan from the whole bank, and the shareable web page has the same plans. To change them, see "Experience tracks" in `interview-coach/README.md`.
The "Coach topic" column below is each bank's main card; a `topic-<id>` tag moves individual questions to the card they belong on.

## Study paths

| Your goal | Time | Do this |
|---|---|---|
| Java interview this week | 5 days | Day 1-2: banks 95 and 96, coding each drill without looking. Day 3: bank 98. Day 4: bank 97. Day 5: bank 89, bank 33 Q1-Q7 and a mock interview. |
| New to GenAI | 1 week | Bank 69 (Q1-Q5, Q9), then bank 67 (Q1-Q6). Build the mini project in bank 67 Q14. Then bank 66 Q1-Q2. |
| Java developer moving to GenAI | 3 weeks | Week 1: bank 69, bank 66. Week 2: banks 67 and 77, and build RAG in Spring AI. Week 3: banks 68 and 78, and build an MCP server and one agent. |
| Senior or architect round | 1 week | Banks 89, 99 Q1, 97 Q5-Q6, 88 Q1, 88 Q4, 68 Q3, 68 Q8, 78 Q10. Practise saying trade-offs aloud. |

---

## Reported rounds

### 35 Java Streams questions for SDE-2

Answered in full in banks [95](../interview-scenarios/95_reported_streams_coding.md) (coding Q1-Q20) and
[96](../interview-scenarios/96_reported_streams_concepts.md) (concepts Q1-Q15), in the same order as the list.
The list's tip about complexity, null handling, duplicate keys, performance, and streams vs loops is the table at the top of bank 95.

### Deloitte (reported: 6+ years)

| # | Question | Answer |
|---|---|---|
| 1 | How do reflection and dynamic proxies work internally? | Bank 97 Q1 |
| 2 | High CPU, frequent GC and progressively rising latency | Bank 07 Q2, Bank 07 Q3, Bank 89 Q3 |
| 3 | PECS with a generic API example | Bank 83 Q7, Bank 70 Q10 |
| 4 | Custom Collector for parallel processing | Bank 97 Q2 |
| 5 | Java modules, boundaries, reflective access | Bank 20 Q28 |
| 6 | Does a new language feature improve maintainability? | Bank 97 Q4 |
| 7 | ReentrantLock, ReadWriteLock, StampedLock or synchronized | Bank 97 Q3 |
| 8 | Intermittent hang from lock contention and database waits | Bank 89 Q3 |
| 9 | Optimise Spring Boot startup | Bank 71 Q11 |
| 10 | Optimistic locking, ETags, conditional requests | Bank 99 Q3 |
| 11 | Passwords, keys and secrets in logs | Bank 89 Q6 |
| 12 | Timeouts, retries, circuit breakers, fallback | Bank 05 Q4, Bank 05 Q5 |
| 13 | How to implement threads | Bank 97 Q9 |
| 14 | SQL vs NoSQL for high-volume financial transactions | Bank 88 Q4 |
| 15 | Pool exhausted though queries are fast | Bank 89 Q4 |
| 16 | Tracing, correlation IDs, logging, metrics | Bank 08 Q2, Bank 72 Q5 |
| 17 | Distributed rate limiting with Redis | Bank 86 Q6, Bank 98 Q13 |
| 18 | Millions of Kafka events per hour in Spring Boot | Bank 89 Q2 |
| 19 | Evolve Kafka schemas without breaking anyone | Bank 74 Q6 |
| 20 | Kafka-based fraud detection with recovery | Bank 89 Q1 |
| 21 | Multi-region Java platform with DR | Bank 73 Q13 |
| 22 | Breaking API and database change with no downtime | Bank 73 Q9, Bank 30 Q20 |

### Mastercard (reported; questions 1-12 weren't visible in the screenshots)

| # | Question | Answer |
|---|---|---|
| 13 | Race condition appears only in production with many threads | Bank 97 Q8 |
| 14 | Timeouts with a shared HashMap, and no crash | Bank 97 Q5 |
| 15 | All requests time out though the app is running | Bank 97 Q6 |
| 16 | In which scenarios do you get concurrency issues? | Bank 97 Q7 |
| 17 | GitHub branching strategies and protection rules | Bank 89 Q5 |
| 18 | Databases used; MVCC in PostgreSQL vs MySQL | Bank 88 Q1 |
| 19 | Cascade types and orphan removal | Bank 88 Q2 |
| 20 | Database-level locking in your code | Bank 88 Q3 |

### Capgemini (Java backend)

| # | Question | Answer |
|---|---|---|
| 1 | Important features in Java 17 | Bank 87 Q2 |
| 2-3 | Why upgrade from 8 to 17, and its advantages | Bank 98 Q18 |
| 4 | Major features in Java 8 | Bank 20 Q50 |
| 5-6 | Default and static methods in interfaces | Bank 93 Q2 |
| 7 | What is the Stream API? | Bank 96 Q1 |
| 8 | What is a method reference? | Bank 20 Q51 (see its follow-ups) |
| 9 | Sort Person objects by age | Bank 95 Q10 |
| 10 | map vs flatMap | Bank 96 Q3 |
| 11 | Why use Spring Boot? | Bank 98 Q20 |
| 12 | What is auto-configuration? | Bank 91 Q6, Bank 85 Q2 |
| 13 | What is @SpringBootApplication? | Bank 21 Q3 |
| 14 | What is @ComponentScan? | Bank 98 Q8 |
| 15 | Circuit breaker | Bank 61 Q1 |
| 16-18 | Service discovery, registering, and the A-to-B flow | Bank 98 Q17, Bank 24 Q8 |
| 19-22 | Worked with Kafka? Spring Kafka, consumers, consumer groups | Bank 22 Q3, Bank 74 Q12, Bank 02 Q1 |
| 23 | How partitions are assigned within a group | Bank 02 Q9 |
| 24 | Can consumers in different groups read one partition? | Bank 22 Q3 (yes: each group has its own offsets) |
| 25-28 | SonarQube and code coverage | Bank 98 Q16 |
| 29 | Performance and security reasons for Java 17 | Bank 98 Q18 |
| 30 | WebSocket | Bank 98 Q15 |
| 31-32 | WebClient, and RestTemplate vs WebClient | Bank 21 Q14 |

### Virtusa (walk-in: one AI round, then two technical rounds)

The AI round covered project experience, Java, Spring Boot, microservices, coding, Kafka and AWS. For that style, practise
with the coach's *Mock interview*, and answer in full sentences. Rehearse a 2-minute project story.

| Round | Question | Answer |
|---|---|---|
| Technical 1 | Pair in an array with a sum nearest a target | Bank 98 Q2 |
| | Explain your project | Bank 94 Q11 (structure; use your own system) |
| | Where do you use Kafka, and why? | Bank 62 Q1 (how Kafka works; add your own use case) |
| | How did you design the Notification Service? | Bank 90 Q6, Bank 22 Q18 |
| | JUnit tests for void methods | Bank 98 Q5 |
| | JUnit tests for static methods | Bank 98 Q6 |
| | Composite key, @Embedded, @Embeddable | Bank 98 Q7 |
| | Write a Controller to register an employee | Bank 98 Q4 |
| | Stream: employees per month, month extraction, monthly order | Bank 98 Q3 |
| | Basic AWS questions | Bank 33 (all 15), starting with Q1, Q2, Q5, Q6 and Q7 |
| Technical 2 | Least coins to reach a target | Bank 98 Q1 |
| | Vertical vs horizontal scaling | Bank 30 Q21 |
| | Explain OAuth and JWT; who creates the JWT? | Bank 98 Q10 |
| | Implement an immutable class | Bank 98 Q9 |
| | Rate limiter, its parameters, and a key without a user id | Bank 98 Q13 |
| | Redis vs in-memory cache | Bank 98 Q14 |
| | Strategy and Factory patterns | Bank 98 Q11 |
| | @RestControllerAdvice vs @ExceptionHandler | Bank 98 Q12 |
| | How do you check Kafka consumer lag? | Bank 02 Q11 |

---

## GenAI study material

### Gen AI fundamentals (40 concepts)

All 40 are in [bank 69](../interview-scenarios/69_genai_fundamentals_40_concepts.md), which opens with a concept-to-answer table.

### Vector Database Handbook

| Handbook section | Answer |
|---|---|
| Fundamentals, traditional vs vector | Bank 67 Q1 |
| Keyword vs semantic vs hybrid | Bank 67 Q8 |
| Vectors, embeddings, how text becomes an embedding | Bank 69 Q1, Bank 67 Q2 |
| Measuring similarity | Bank 67 Q3 |
| What a vector database stores | Bank 67 Q5 |
| How vector search works; exact, ANN, HNSW | Bank 67 Q4 |
| Mini project: load, chunk, embed, insert, search | Bank 67 Q14 |
| Chunking | Bank 67 Q6 |
| Metadata filters | Bank 67 Q7 |
| Update, delete and persist | Bank 67 Q11 |
| Improving retrieval quality | Bank 67 Q9, Bank 67 Q10 |
| Connect to RAG | Bank 67 Q14, Bank 77 Q3 |

### Agentic AI study notes

| Notes section | Answer |
|---|---|
| 1. Introduction, chatbot vs agent, autonomy levels | Bank 68 Q1, Bank 68 Q3 |
| 2. Anatomy of an agent, the loop, when to stop | Bank 68 Q2 |
| 3. LLMs, system prompts, choosing a model, context engineering | Bank 69 Q5, Bank 69 Q6, Bank 69 Q10 |
| 4. Tool use and function calling | Bank 68 Q5, Bank 69 Q9 |
| 5. Memory | Bank 68 Q6, Bank 69 Q11 |
| 6. RAG for agents, classic vs agentic | Bank 67 Q12 |
| 7. Planning and reasoning patterns | Bank 68 Q4 |
| 8. MCP, and MCP vs A2A | Bank 68 Q7, Bank 68 Q9 |

Pages 10-19 of those notes hadn't been shared when this was written.

### Spring AI Recipes (Craig Walls)

[The 73 recipes](https://www.habuma.com/springairecipes/) are short, hands-on articles. Read them for working code. The table
says which interview answer covers each topic. **The articles themselves were not readable when this was written (the host
returned 403), so answers rely on the recipe titles and on the Spring AI reference docs, not on the articles' code.**

| Recipes | Answer |
|---|---|
| Building a Text-Based Chat Loop; A No-Build Chat Loop with JBang; Composing ChatClient Behavior | Bank 66 Q1, Bank 66 Q2 |
| Logging LLM Requests and Responses; Better Logging with ToolCallAdvisor | Bank 66 Q3 |
| Using More than One LLM | Bank 66 Q4 |
| Enabling Resilient Structured Output | Bank 66 Q5 |
| Summarizing Chat Memory; Persisting Chat Memory with JDBC; 3 More Ways to Persist Chat Memory; Enabling Long-Term Memory | Bank 66 Q6, Bank 68 Q6 |
| Semantic Caching (with Redis); Semantic Caching with Any Vector Store | Bank 66 Q7 |
| Running Against Local LLMs; Running Against an in-JVM Model; Running LLMs in the JVM with Qxotic; Running System One Models Locally | Bank 66 Q8, Bank 66 Q12 |
| Switching to the OpenAI Responses API; Running Python with Hosted Code Interpreter | Bank 66 Q9 |
| Talking to AI; Adding Voice to AI; Using ElevenLabs Voices | Bank 66 Q10 |
| Applying Input Guardrails with SafeGuardAdvisor; Safeguarding LLM Output; Applying Semantic Guardrails | Bank 66 Q11 |
| Fact-Checking AI Responses; Decomposing Answers into Claims; Fact-Checking with a System One Model; Making AI Judgements with Jev | Bank 66 Q12 |
| Essential RAG; Filtering RAG Results with Metadata | Bank 77 Q3, Bank 67 Q7 |
| Better RAG Results with HyDE; Better RAG Results with Reranking | Bank 67 Q9 |
| Better RAG Results with Hybrid Search | Bank 67 Q8 |
| Tool-Based RAG; Making RAG Conversation-Aware | Bank 67 Q12 |
| RAG Without a Separate Vector Database; Speeding up RAG with Faster Embeddings | Bank 67 Q13 |
| Reasoning and Acting (ReAct) | Bank 68 Q4 |
| Efficient Tool Use; Explaining Tool Selection | Bank 68 Q5, Bank 66 Q3 |
| Creating an STDIO MCP Server; Streamable HTTP MCP Server; Creating an MCP Client; No-Build MCP with JBang | Bank 78 Q3, Bank 68 Q7 |
| Defining MCP Prompts; MCP Prompt Completions; MCP Logging; MCP Sampling; MCP Elicitation; MCP Tool Progress | Bank 68 Q7 |
| Securing an MCP Server with an API Key; Securing an MCP Server with OAuth; Controlling MCP Tool Visibility | Bank 68 Q8 |
| Enabling Agent-to-Agent Communication with A2A; Invoking A2A Sub-Agents with TaskTool; Defining Claude-Style Subagents | Bank 68 Q9 |
| Guiding Agentic Behavior with Skills; Reusing Agent Behavior with SkillsJars; Agentic Planning with TodoWriteTool; Asking Questions to the User | Bank 68 Q10 |
| Building a Graph-Based Agentic Workflow; Adding a Loop; Adding Human-in-the-Loop; with LangGraph4j; Visualizing Spring AI Alibaba Graph Workflows | Bank 68 Q11 |
| Getting Started with Embabel; Modeling Agent State in Embabel; Human-in-the-Loop in Embabel; Invoking an Embabel Agent in Java | Bank 68 Q12 |
| Adding a Web UI with AG-UI and CopilotKit; Rendering Rich UIs with MCP Apps; Rendering MCP Apps UIs in an AG-UI/CopilotKit Client | Bank 68 Q13 |

"Next areas to watch" from the post that shared the recipes: Responses API (Bank 66 Q9), hosted tools and session memory (Bank 66 Q9), Agentic GraphRAG with Neo4j (Bank 68 Q15), and advanced autonomous agents (Bank 68 Q15).

### Other sources

| Source | Answer |
|---|---|
| Java + Spring AI, Day 3: understanding ChatClient | Bank 66 Q1 |
| 12 API design patterns | Bank 99 Q1 |
| Spring Boot 1.0 vs 2.0 vs 3.0 vs 4.0 | Bank 98 Q19 |
| Anthropic Claude agentic AI ecosystem | Bank 68 Q14 |

### 25 repositories for AI agent developers (PDF)

Free resources, grouped by what you need. The PDF lists names only, so links were worked out from those names and its page
images, then opened to confirm they exist. **Check the content before relying on one**, and check the licence before using its code.

| # | Resource | Use it for |
|---|---|---|
| | **Start with agents and GenAI** | |
| 1 | [Agentic AI Crash Course](https://github.com/aishwaryanr/awesome-generative-ai-guide) | Short course: agents, tools, RAG, MCP, planning |
| 3 | [ai-agents-for-beginners](https://github.com/microsoft/ai-agents-for-beginners) | 11 Microsoft lessons, a good first course |
| 5 | [GenAI_Agents](https://github.com/NirDiamant/GenAI_Agents) | Agent tutorials from simple to multi-agent |
| 11 | [agents-towards-production](https://github.com/NirDiamant/agents-towards-production) | Memory, deployment, security, observability |
| | **RAG, prompts and context** | |
| 4 | [RAG_Techniques](https://github.com/NirDiamant/RAG_Techniques) (the PDF prints "AG_Techniques") | Advanced retrieval methods |
| 8 | [Prompt-Engineering-Guide](https://github.com/dair-ai/Prompt-Engineering-Guide) | Prompting reference |
| 15 | [Context-Engineering](https://github.com/jasontang-ai/Context-Engineering) | From prompts to context design |
| | **How LLMs work** | |
| 7 | [Hands-On-Large-Language-Models](https://github.com/HandsOnLLM/Hands-On-Large-Language-Models) | Book notebooks, very visual |
| 13 | [llm-course](https://github.com/mlabonne/llm-course) | Fundamentals, scientist and engineer tracks |
| 17 | [nn-zero-to-hero](https://github.com/karpathy/nn-zero-to-hero) | Build neural networks from scratch |
| | **MCP and tools** | |
| 9 | [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) | Server catalogue; vet any server before running it |
| 10 | [n8n-workflows](https://github.com/Zie619/n8n-workflows) ("1000+ Pre-Built AI Agents") | Automation workflows to borrow ideas from, and these are n8n workflows rather than agents as such |
| | **Project ideas** | |
| 12 | [Hands-On-AI-Engineering](https://github.com/Sumanth077/Hands-On-AI-Engineering) | Agent and RAG apps |
| 14 | [500-AI-Agents-Projects](https://github.com/ashishpatel26/500-AI-Agents-Projects) | Use cases by industry |
| 24 | [awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) | Runnable LLM apps |
| 25 | [awesome-ai-apps](https://github.com/Arindam200/awesome-ai-apps) | Runnable AI apps |
| | **Lists and roadmaps** | |
| 2 | [awesome-generative-ai](https://github.com/steven2358/awesome-generative-ai) | Broad, curated list |
| 6 | [AI-ML-Roadmap-from-scratch](https://github.com/aadi1011/AI-ML-Roadmap-from-scratch) | A full path, with free resources |
| | **Only if your role needs them** | |
| 16 | [ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) | Classic ML, 12 weeks |
| 18 | [awesome-computer-vision](https://github.com/jbhuang0604/awesome-computer-vision) | Computer vision |
| 19 | [awesome-nlp](https://github.com/keon/awesome-nlp) | NLP |
| 20 | [awesome-datascience](https://github.com/academic/awesome-datascience) | Data science |
| 21 | [all-rl-algorithms](https://github.com/FareedKhan-dev/all-rl-algorithms) | Reinforcement learning implementations |
| 22 | [awesome-rl](https://github.com/aikorea/awesome-rl) | Reinforcement learning list |
| 23 | [Made-With-ML](https://github.com/GokuMohandas/Made-With-ML) | MLOps |

A Java developer should start with 3, 4 and 8, and then 11. Most are in Python, and the concepts carry straight over to Spring AI.

### Google free AI courses (from an infographic)

The nine topics, in the order the graphic gives: introduction to cloud computing, prompt engineering in Vertex AI, Google AI
Essentials (Coursera), what is generative AI, large language models explained, AI principles in Google Cloud, programming
basics, cloud computing foundations, responsible AI practices. Its own advice is sensible: pick 2 or 3 that match your level, and apply
what you learn. **Exact course names, price and certificates weren't verified, so confirm them on Google's site before enrolling.** Courses
back up a project; they don't replace one.

---

## Corrections to the source material

Checked against primary sources on 2026-11-03. Don't repeat the left column in an interview.

| The source says | What the sources say | Checked against |
|---|---|---|
| Spring Boot 4 requires Java 21+ | Minimum is **Java 17**; compatible up to Java 25 | Spring Boot 4.0 system requirements |
| Spring Boot 2.0 requires Tomcat 9 | Minimum was **Tomcat 8.5** | Spring Boot 2.0 M1 release notes |
| Spring Boot 1.0 requires Java 8 | The oldest docs online (1.2.x) say **Java 6** | Spring Boot 1.2 reference docs |
| Boot 4 is "AI-ready" | Spring AI is a **separate project** | Spring AI 2.0 GA announcement |
| Mixture-of-experts has Code, Math and Reasoning experts | A teaching simplification; experts are learned | General knowledge of MoE models |
| A2A "started by Google" (notes) | True, and **now at the Linux Foundation** since June 2025 | Linux Foundation |
| MCP sampling and elicitation (several sources) | **Reworked** in the 2026-07-28 spec; sampling, roots and logging deprecated | MCP changelog |
| Simple word chunker (handbook) | Works, but emits a redundant tail chunk; bank 67 Q6 has the fix | Ran it |
| "Anthropic ecosystem" product labels | Some match official products, and others couldn't be found | Bank 68 Q14 |
| "1000+ Pre-Built AI Agents" (PDF) | The page image shows a collection of n8n workflows | Its page image |

Ads for paid guides and PDF kits in the screenshots were left out. Nothing here depends on them.

## Known gaps

- **Mastercard questions 1-12**, and **Agentic AI notes pages 10-19** weren't visible in what was shared. Handbook page 19 is also missing.
- **Spring AI recipe code**, because the articles returned 403. Read them directly for working examples.
- DSA topics such as heaps, LCA and graph algorithms beyond bank 50 are still outside this pack.

## Adding more material

1. Check whether it's already answered: search the coach, or the question titles in `../interview-scenarios/`.
2. Add a row to the right table above, pointing to the answer.
3. For a real gap, add a question to the matching bank in the format shown in `../interview-scenarios/README.md`, or start a new bank and add it to the table at the top.
4. Verify claims against primary sources, and add any wrong ones to the corrections table. If it can run, put it in `examples/`.
5. Run the coach's `tests/test_real_repo.py`. It checks format and wiring, and that every "Bank N Qm" reference in this pack points to a question that exists.

## Sources (checked 2026-11-03)

Shared by the repo owner: LinkedIn and Instagram posts on Deloitte, Mastercard, Capgemini and Virtusa interviews (some authors
named in the posts themselves, such as Hema Madhala for Virtusa), "35 Java Streams Questions", "Agentic AI Complete Developer Study Notes" (Brij Kishore Pandey),
"Vector Database Handbook" (aman_views), "40 Gen AI Fundamentals" (datasciencebrain), "12 API Design Patterns" (Arslan Ahmad / DesignGurus),
"Spring Boot 1.0 vs 4.0" (Mohamed El Laithy), "Anthropic Claude Agentic AI Ecosystem" (Rakesh Gohel), a Google courses graphic (Steve Nouri),
"Java + Spring AI" (Saikiran), and "25 Repos for AI Agent Developers" (Om Nalinde).

Checked against:
- [Spring AI Recipes](https://www.habuma.com/springairecipes/) (Craig Walls)
- Spring AI reference: [advisors](https://docs.spring.io/spring-ai/reference/api/advisors.html), [RAG](https://docs.spring.io/spring-ai/reference/api/retrieval-augmented-generation.html), [chat memory](https://docs.spring.io/spring-ai/reference/api/chat-memory.html), [MCP](https://docs.spring.io/spring-ai/reference/api/mcp/mcp-overview.html)
- [Spring AI 2.0.0 GA](https://spring.io/blog/2026/06/12/spring-ai-2-0-0-GA-available-now/), [Spring AI 2.1.0-M1](https://spring.io/blog/2026/09/25/spring-ai-2-1-0-M1-available-now/), [Spring AI and TypeSafe Jev](https://spring.io/blog/2026/09/21/spring-ai-typesafe-structured-judgment)
- [Spring Boot 4.0 system requirements](https://docs.spring.io/spring-boot/4.0/system-requirements.html), [4.0 migration guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide), [2.0.0 M1 release notes](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.0.0-M1-Release-Notes), [1.2 system requirements](https://docs.spring.io/spring-boot/docs/1.2.1.RELEASE/reference/html/getting-started-system-requirements.html), [InfoQ on Spring 7 and Boot 4](https://www.infoq.com/news/2025/11/spring-7-spring-boot-4)
- [MCP 2026-07-28 changelog](https://modelcontextprotocol.net/specification/2026-07-28/changelog.md), [WorkOS on the stateless spec](https://workos.com/blog/mcp-stateless-spec-2026-07-28), [The Register on compatibility](https://www.theregister.com/a/5276722)
- [A2A at one year (Linux Foundation)](https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year?hs_amp=true)
- [Claude Managed Agents](https://claude.com/platform/claude-managed-agents), [Managed Agents memory](https://platform.claude.com/docs/en/managed-agents/memory), [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview), [Claude memory including Cowork](https://claude.com/blog/claudes-memory-works-everywhere-and-you-decide-whats-in-it)
- AWS: [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html), [S3 consistency](https://aws.amazon.com/s3/consistency/), [SQS queue types](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-queue-types.html), [SQS quotas](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/quotas-messages.html), [ALB vs NLB](https://aws.amazon.com/compare/the-difference-between-the-difference-between-application-network-and-gateway-load-balancing/)
- Embabel: [InfoQ](https://infoq.com/news/2025/06/introducing-embabel-ai-agent), [The New Stack](https://thenewstack.io/spring-creator-java-type-system-agentic-ai-rod-johnson/)
