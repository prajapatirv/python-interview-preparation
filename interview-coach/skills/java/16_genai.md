---
id: genai
title: GenAI architecture for Java (RAG, MCP, agents)
order: 16
summary: LLM fundamentals, RAG, vector stores, Spring AI / LangChain4j, tool calling, MCP servers, agents, guardrails, evaluation and LLMOps.
keywords: genai, gen ai, generative ai, llm, large language model, rag, retrieval-augmented, retrieval augmented, embedding, embeddings, vector database, vector store, vector db, mcp, model context protocol, prompt engineering, prompt injection, spring ai, langchain4j, ai agent, agentic, hallucination, fine-tuning, fine tuning, chunking, guardrail, guardrails, chatbot, ollama, semantic search, re-ranking, reranking
---
Skill focus for GenAI architecture answers (Java/J2EE + Gen AI profile):
- Stay vendor-neutral: name the abstraction (Spring AI `ChatClient`, `EmbeddingModel`, `VectorStore`; LangChain4j `AiServices`) and say the model can be OpenAI-compatible, Azure OpenAI, AWS Bedrock, Vertex or a local open-weight model on Ollama/vLLM.
- Frame every answer as a functional requirement (an HR policy assistant, a support-ticket copilot, an order-lookup agent) with the non-functional ones made explicit: latency budget, cost per request, data privacy, accuracy target.
- Treat the LLM as an unreliable, slow, expensive remote dependency: timeouts, retries with backoff, circuit breaker, fallback, token budgets, caching, and observability of tokens and latency.
- RAG answers must cover both pipelines: ingestion (read, chunk, embed, store with metadata) and query (rewrite, retrieve, re-rank, augment, generate, cite). Name how retrieval quality is measured.
- MCP answers: host / client / server roles, tools vs resources vs prompts, stdio vs Streamable HTTP, the 2026-07-28 spec making the protocol stateless, and security (OAuth 2.1, least privilege, tool poisoning, human approval for destructive tools).
- Always mention guardrails (prompt injection, PII redaction, output validation) and evaluation (golden sets, faithfulness, LLM-as-judge with care).
- Versions as of late 2026: Spring AI 2.0.x on Spring Boot 4, LangChain4j 1.x, MCP spec 2026-07-28. Say "check the version your team runs" when an API name is version-sensitive.
