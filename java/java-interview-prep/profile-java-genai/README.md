# Profile pack: Java/J2EE + Gen AI

Preparation for the resource-requirement evaluation (PM/DM round) with this skill set:

| Field | Requirement |
|---|---|
| Primary skill | Java/J2EE |
| Sub-skill | **Gen AI** |
| Summary | Core Java and Spring Boot · MVC · Cloud microservice architecture · Event-driven architecture and containerization · REST API |

**160 questions in total**: 7 technical sections × 15, plus 25 GenAI architecture questions, plus a 25-question company
pack. Every answer starts from a **functional requirement** (what the business asks for), then walks through the
answer, trade-offs, monitoring, likely follow-ups, and a **60-second answer** to say out loud.

GenAI answers are **vendor-neutral**: Spring AI 2.0 / LangChain4j 1.x against any OpenAI-compatible API, Azure OpenAI,
AWS Bedrock, Vertex AI or local open-weight models (Ollama, vLLM). They don't depend on any one provider.

## The sections

| # | Section | File | Questions |
|---|---|---|---|
| 1 | Core Java | [70_profile_core_java.md](../interview-scenarios/70_profile_core_java.md) | 15 |
| 2 | Spring Boot | [71_profile_spring_boot.md](../interview-scenarios/71_profile_spring_boot.md) | 15 |
| 3 | Spring MVC | [72_profile_spring_mvc.md](../interview-scenarios/72_profile_spring_mvc.md) | 15 |
| 4 | Cloud microservice architecture | [73_profile_cloud_microservices.md](../interview-scenarios/73_profile_cloud_microservices.md) | 15 |
| 5 | Event-driven architecture | [74_profile_event_driven.md](../interview-scenarios/74_profile_event_driven.md) | 15 |
| 6 | Containerization (Docker, Kubernetes) | [75_profile_containerization.md](../interview-scenarios/75_profile_containerization.md) | 15 |
| 7 | REST API | [76_profile_rest_api.md](../interview-scenarios/76_profile_rest_api.md) | 15 |
| 8 | GenAI architecture I: LLM basics, RAG, vector stores, evaluation | [77_profile_genai_rag_llm.md](../interview-scenarios/77_profile_genai_rag_llm.md) | 13 |
| 9 | GenAI architecture II: tool calling, **MCP servers**, agents, A2A, guardrails, LLMOps | [78_profile_genai_agents_mcp.md](../interview-scenarios/78_profile_genai_agents_mcp.md) | 12 |
| C | Company pack: Chase Travel Java rewrite and migration | [../company-chase-travel/README.md](../company-chase-travel/README.md) | 25 |

## Where these questions are used

Every bank file is read automatically by the **Interview Coach** (`interview-coach/`, start with `start.cmd`, then open
http://127.0.0.1:8100, **Java** stack). No code change was needed: each file's front-matter `skill:` decides its topic card.

| # | Section | Bank file | Questions | Coach topic card (Topics screen) | Coach `skill:` id |
|---|---|---|---|---|---|
| 1 | Core Java | `70_profile_core_java.md` | 15 | Java 8, Java 11 & modern Java | `java-core` |
| 2 | Spring Boot | `71_profile_spring_boot.md` | 15 | Spring & Spring Boot | `spring-boot` |
| 3 | Spring MVC | `72_profile_spring_mvc.md` | 15 | Spring & Spring Boot | `spring-boot` |
| 4 | Cloud microservices | `73_profile_cloud_microservices.md` | 15 | Microservices architecture | `microservices` |
| 5 | Event-driven architecture | `74_profile_event_driven.md` | 15 | Apache Kafka | `kafka` |
| 6 | Containerization | `75_profile_containerization.md` | 15 | Cloud, Docker & Kubernetes | `cloud-devops` |
| 7 | REST API | `76_profile_rest_api.md` | 15 | REST APIs & third-party integration | `rest-api` |
| 8 | GenAI I: LLM, RAG, vector stores | `77_profile_genai_rag_llm.md` | 13 | **GenAI architecture for Java (RAG, MCP, agents)** (new card) | `genai` |
| 9 | GenAI II: tools, MCP, agents | `78_profile_genai_agents_mcp.md` | 12 | **GenAI architecture for Java (RAG, MCP, agents)** (new card) | `genai` |
| C1 | Chase Travel: rewrite and migration | `80_company_chase_travel_migration.md` | 15 | System design & design patterns | `architecture` |
| C2 | Chase Travel: travel platform design | `81_company_chase_travel_domain.md` | 10 | System design & design patterns | `architecture` |
| | **Total** | | **155** | | |

How each coach screen uses them:

| Coach screen | What you get from this pack |
|---|---|
| **Topics** | Open the topic card from the table above; these questions are listed as *scenario* answers, shown first |
| **Ask anything** | Type a question such as "how do I secure an MCP server?"; the answer is grounded on these banks |
| **Mock interview** | Pick a topic (e.g. GenAI architecture) and answer under interview conditions; scored against these answers |
| **Job description** | Paste the requirement text (Core Java, Spring Boot, MVC, cloud microservices, event-driven, containers, REST, Gen AI) to get a study plan pointing at these topics |
| **Progress / Review** | Mark questions as practised and revisit weak ones |
| **Coverage** | Lists every bank file above as wired in; the canary test fails if one ever drops out |

Files live in [`../interview-scenarios/`](../interview-scenarios/); the coach topic definition for the GenAI card is
`interview-coach/skills/java/16_genai.md`.

## How the GenAI part fits the Java part

The evaluators will probe whether you can build GenAI features *as a Java architect*: the model is just another
slow, expensive, unreliable remote dependency, and RAG ingestion is an event-driven pipeline. Keep that framing.

```text
 Web / Mobile ──> API Gateway ──> Feature services (Spring Boot, Spring AI ChatClient)
                                       │        │               │
                         RAG retrieval │        │ tools / MCP   │ every model call
                                       v        v               v
             Vector + keyword store   MCP servers (orders,   AI gateway: auth, quotas, PII redaction,
             (pgvector / OpenSearch)  CRM, HR) wrap REST     routing, fallback, token & cost logging
                     ^                APIs, OAuth 2.1             │
                     │                                            v
  Sources ─> Kafka ─> parse ─> chunk ─> embed ─> index    Models: cloud platforms or self-hosted
  (CDC, files, SaaS)   (event-driven ingestion, KEDA)     open-weight models (vLLM on GPU nodes)

  Cross-cutting: OpenTelemetry traces (gen_ai.* attributes), evaluation gates in CI, guardrails starter,
                 Kubernetes + GitOps, secrets in a vault.
```

## Must-practise list (say these out loud first)

1. Core Java Q5: CompletableFuture fan-out with a time budget
2. Core Java Q6: virtual threads, when they help and when they don't
3. Core Java Q15: thread-safe rate limiter for LLM calls (bridges Java and GenAI)
4. Spring Boot Q1: how auto-configuration works
5. Spring Boot Q3: `@Transactional` pitfalls
6. Spring Boot Q12: upgrade from 2.7 / Java 8 to Boot 4 / Java 25
7. MVC Q1: the DispatcherServlet request flow
8. MVC Q9: streaming LLM tokens with SSE
9. Microservices Q1: strangler-fig decomposition
10. Microservices Q2: sagas across services
11. EDA Q3: idempotent consumers and exactly-once
12. EDA Q4: transactional outbox
13. EDA Q15: event-driven ingestion pipeline feeding RAG
14. Containers Q2: JVM memory in containers / OOMKilled
15. Containers Q5: probes and graceful shutdown
16. REST Q2: idempotency keys
17. GenAI I Q3: RAG pipeline with Spring AI
18. GenAI I Q6: improving retrieval (hybrid search, re-ranking)
19. GenAI I Q8: evaluating RAG
20. GenAI II Q2–Q4: MCP: what it is, building a Spring Boot MCP server, securing it
21. GenAI II Q5: agents vs workflows
22. GenAI II Q10: reference architecture of an enterprise GenAI platform

## A 10-day plan

| Day | Focus | Output |
|---|---|---|
| 1 | Core Java 1–15 | 60-second answers for Q3, Q5, Q6, Q8, Q15 recorded and replayed |
| 2 | Spring Boot 1–15 | Draw the auto-config and transaction-proxy mechanisms from memory |
| 3 | Spring MVC 1–15 | Whiteboard the request flow; write the SSE endpoint from memory |
| 4 | Microservices 1–15 | Draw saga + outbox + CQRS for a booking flow |
| 5 | Event-driven 1–15 | Explain partitions/keys/ordering and DLT strategy without notes |
| 6 | Containers 1–15 | Write a Deployment with probes, resources and PDB from memory |
| 7 | REST 1–15 | Design an API (resources, errors, idempotency, pagination) for a new domain in 20 minutes |
| 8 | GenAI I (RAG) | Draw both RAG pipelines; explain chunking, hybrid search, evaluation |
| 9 | GenAI II (MCP, agents) | Explain MCP roles/primitives/transports and security; sketch the platform diagram |
| 10 | Company pack + mock | Coach mock interview; rehearse the self-introduction and project story |

## Self-introduction template (fill with your real experience)

> "I'm a Java backend engineer with N years on Java/J2EE and Spring Boot, building microservices and REST APIs,
> event-driven systems on Kafka, deployed in containers on Kubernetes in the cloud. Most recently I [your real project:
> domain, scale, your role, one measurable result]. Over the last year I've been building GenAI capabilities on the JVM:
> RAG pipelines with Spring AI and vector stores, tool calling and MCP servers that expose our services to AI
> assistants, with guardrails, evaluation and cost monitoring. I enjoy turning an LLM prototype into a production
> service that's observable, secure and affordable."

Only claim what you have done or built. If GenAI experience is from personal projects or proofs of concept, say so;
evaluators respect "here's what I built and what I learned" far more than inflated claims.

## Questions to ask the PM/DM

1. Which GenAI use cases are in scope: RAG/knowledge assistants, agents with tool access, document processing?
2. Which model providers or platforms are approved (cloud platform, self-hosted), and what are the data-residency rules?
3. Is the Java estate on Spring Boot 3 or 4, and which Java version? Any migration work in scope?
4. What does the event backbone look like (Kafka, cloud queues)? Which container platform (EKS, AKS, OpenShift)?
5. How is quality of GenAI features measured today (evaluation sets, feedback)?
6. Team shape: how many Java developers, is there an ML/data team, who owns the AI platform?
