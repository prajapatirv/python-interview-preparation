---
id: profile-java-genai-rag-llm
title: Java + GenAI profile (8/9): GenAI architecture I, LLM fundamentals and RAG on the JVM (13 questions)
stack: java
skill: genai
---
Part of the **Java/J2EE + Gen AI** profile pack (see `../profile-java-genai/README.md`). GenAI questions 1–13 of 25.

**Vendor-neutral on purpose.** Code uses the Spring AI 2.0 abstractions (`ChatClient`, `EmbeddingModel`, `VectorStore`) or
LangChain4j 1.x, which run against any OpenAI-compatible API, Azure OpenAI, AWS Bedrock, Google Vertex AI, or local
open-weight models on Ollama/vLLM. API names are as of late 2026; check the exact version your team runs.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [mid] Explain how an LLM-powered feature works end to end, from tokens to response.
tags: llm, tokens, context-window, temperature, embeddings, inference, genai-basics, profile-java-genai

**Start here: the concepts**
- **LLM:** a model trained to predict the next **token** (a word piece, roughly ¾ of an English word). Generation is repeated next-token prediction.
- **Context window:** the maximum tokens (prompt + response) the model can attend to in one call, from tens of thousands to over a million depending on the model.
- **Prompt roles:** **system** (instructions/persona), **user** (the question), **assistant** (previous answers), **tool** (tool results).
- **Sampling:** `temperature` (randomness; 0–0.3 for factual tasks), `top_p`, `max_tokens` (cap on output length and cost).
- **Embeddings:** a different model turns text into a vector of numbers so that similar meanings are close; the basis of semantic search and RAG.
- **Stateless:** the model remembers nothing between calls; "memory" is the application resending history.

**The live scenario (functional requirement)**
*FR: "Build an HR policy assistant: employees ask questions like 'How many days of paternity leave do I get?' and get an answer with the policy source, in under 5 seconds."*

**What the interviewer is really checking**
That you understand what the model does and doesn't do, and where the application has to do the work.

**How I answer it**
1. The Java service receives the question, and **retrieves** relevant policy passages (RAG, because the model has never seen our policies).
2. It builds a **prompt**: system message ("Answer only from the provided policy excerpts; cite the document; say 'I don't know' otherwise"), the excerpts, and the user question.
3. Tokens in = system + excerpts + question; tokens out capped by `max_tokens`. **Cost and latency scale with both**; output tokens are slower and pricier.
4. Calls the model through an abstraction: `chatClient.prompt().system(sys).user(question).call().content()`, with a **low temperature** for consistency.
5. **Streams** the answer to the UI for a fast first token.
6. Records token usage, latency and the sources used, for cost tracking and audit.
7. The model could be a hosted API or a self-hosted open-weight model; the code doesn't change.

**Trade-offs and what can go wrong**
- **Hallucination:** fluent but wrong answers, especially without grounding.
- **Context limits and "lost in the middle":** stuffing too much text dilutes attention and raises cost; retrieve less but better.
- **Non-determinism:** even at temperature 0 outputs can vary; tests must use thresholds.
- **Knowledge cutoff:** the model doesn't know recent or private facts; that's what retrieval is for.

**How I'd monitor it**
Latency (time to first token, total), tokens in/out per request, cost per conversation, "I don't know" rate, thumbs up/down.

**Follow-ups to expect**
- *What is a token limit error?* -> Prompt + max output exceeds the context window; trim history or context.
- *Why low temperature?* -> Factual, policy-bound answers should be consistent; creativity isn't the goal.
- *Embedding model vs chat model?* -> Embedding models output vectors for search; chat models generate text.

**60-second answer**
"An LLM predicts tokens, knows nothing about our policies and remembers nothing between calls. So for an HR assistant the application does the work: retrieve the relevant policy passages, build a prompt with a system instruction to answer only from them and cite sources, add the question, and call the model at a low temperature with capped output tokens, streaming the reply. Cost and latency scale with tokens in and out, so I keep the context focused, and I log tokens, latency and sources for every answer."

### Q2 [senior] RAG, fine-tuning or prompt engineering: how do you decide?
tags: rag, fine-tuning, prompt-engineering, lora, knowledge, architecture-decision, profile-java-genai

**Start here: the concepts**
- **Prompt engineering:** better instructions and examples in the prompt; cheapest, fastest to iterate.
- **RAG (retrieval-augmented generation):** fetch relevant documents at query time and put them in the prompt; adds **knowledge** that changes.
- **Fine-tuning:** further train a model on examples (often parameter-efficient, e.g. LoRA) to change **behaviour, style or format**; poor at injecting facts that change.

**The live scenario (functional requirement)**
*FR: "A support copilot must answer from 20,000 knowledge-base articles that change daily, always in the company's tone, and output a fixed JSON format for the ticketing system."*

**What the interviewer is really checking**
That you match each technique to the problem: knowledge vs behaviour.

**How I answer it**
1. **Knowledge that changes daily -> RAG.** Updating an index takes minutes; retraining takes days and can't cite sources.
2. **Tone -> prompt engineering first:** a system prompt with style rules and 2–3 examples (few-shot).
3. **Fixed JSON -> structured output** (JSON schema / the framework's entity mapping), not fine-tuning.
4. **Fine-tuning only if** after the above, the model still fails at a narrow, stable behaviour (a domain-specific classification at high volume where a small fine-tuned model beats a big general one on cost/latency).
5. Order of attempts: prompt -> RAG -> structured output/tools -> evaluation -> fine-tune if justified by metrics.

**Trade-offs and what can go wrong**
- Fine-tuning needs curated data, MLOps and re-tuning when the base model changes; it doesn't give citations or access control.
- RAG quality is capped by retrieval quality; garbage in, confident garbage out.
- Long prompts cost tokens on every call; caching stable prefixes helps.

**How I'd monitor it**
Evaluation scores per approach on the same golden set: accuracy, groundedness, format validity, cost and latency.

**Follow-ups to expect**
- *Can you combine them?* -> Yes: a fine-tuned small model with RAG is common for high-volume domains.
- *What about long-context models instead of RAG?* -> Possible for small corpora; for 20,000 articles retrieval is cheaper, faster and more accurate, and supports access control.
- *What is LoRA?* -> Training small adapter matrices instead of all weights; cheaper fine-tuning.

**60-second answer**
"I separate knowledge from behaviour. Knowledge that changes daily, like 20,000 KB articles, is RAG: re-indexing takes minutes, answers can cite sources and respect access control. Tone comes from the system prompt with a few examples, and a fixed JSON format from structured output against a schema. I'd fine-tune only when evaluation shows a narrow, stable behaviour still failing, or a small tuned model would cut cost at high volume. The order is prompt, RAG, structured output, then fine-tune if the metrics justify it."

### Q3 [senior] Design a RAG pipeline in Java with Spring AI: ingestion and query.
tags: rag, spring-ai, vectorstore, embeddings, etl, questionansweradvisor, retrievalaugmentationadvisor, profile-java-genai

**Start here: the concepts**
- **Ingestion (offline):** read -> clean -> chunk -> embed -> store vectors + metadata.
- **Query (online):** (rewrite) -> embed the question -> similarity search top-k -> (re-rank) -> augment the prompt -> generate -> cite.
- **Spring AI building blocks:** `DocumentReader` (PDF, Tika, JSON), `TokenTextSplitter`, `EmbeddingModel`, `VectorStore` (pgvector, Elasticsearch, OpenSearch, Redis, Milvus, Qdrant, Weaviate, Chroma, MongoDB Atlas...), `ChatClient` with **advisors** (`QuestionAnswerAdvisor`, or the modular `RetrievalAugmentationAdvisor`).

**The live scenario (functional requirement)**
*FR: "Insurance agents ask questions over 8,000 policy PDFs; answers must cite the clause; only documents of the agent's region are searchable."*

**What the interviewer is really checking**
A complete, production-minded design and familiarity with the Java tooling.

**How I answer it**
1. **Ingestion service** (event-driven, see the EDA pack):
   - `PagePdfDocumentReader`/`TikaDocumentReader` -> `Document`s with metadata (`docId`, `title`, `clause`, `page`, `region`, `version`).
   - `TokenTextSplitter` (e.g. ~500 tokens, overlap ~50) keeping section headings in each chunk.
   - `vectorStore.add(chunks)` embeds with the configured `EmbeddingModel` and stores vectors + metadata (pgvector with an HNSW index).
2. **Query path:**

```java
var advisor = QuestionAnswerAdvisor.builder(vectorStore)
    .searchRequest(SearchRequest.builder().topK(5).similarityThreshold(0.6).build()).build();
String answer = chatClient.prompt().user(question)
    .advisors(advisor, a -> a.param(QuestionAnswerAdvisor.FILTER_EXPRESSION, "region == '" + region + "'"))
    .call().content();
```

   (In production I'd build the filter with the `FilterExpressionBuilder`, never string-concatenate user input.)
3. **System prompt:** answer only from the context, cite `docId` + clause, say "not found in the policies" otherwise.
4. **Return citations:** the retrieved documents' metadata go back to the UI alongside the answer (from the advisor context).
5. For advanced flows, `RetrievalAugmentationAdvisor` with query transformers (rewrite, translation), multi-query expansion and a document post-processor for re-ranking.
6. Evaluate retrieval and answers on a golden set before launch (Q8).

**Trade-offs and what can go wrong**
- Chunking that splits a clause from its heading loses meaning.
- Changing the embedding model requires re-embedding everything.
- Metadata filters must be enforced server-side from the authenticated user, never from the client request.

**How I'd monitor it**
Retrieval latency, top-k similarity scores (a falling average signals drift), "not found" rate, citation click-through, answer feedback.

**Follow-ups to expect**
- *Same in LangChain4j?* -> `EmbeddingStoreIngestor` with `DocumentSplitters.recursive(500, 50)`, then `AiServices` with an `EmbeddingStoreContentRetriever`.
- *Where do you store original text?* -> In the vector store's content field and/or a document store, referenced by id.
- *How fresh is the index?* -> Event-driven ingestion keeps it within minutes.

**60-second answer**
"Two pipelines. Ingestion reads the PDFs, attaches metadata like doc id, clause, page and region, splits into roughly 500-token chunks that keep their headings, and writes them to a vector store such as pgvector, which embeds them through the configured embedding model. Query time, a Spring AI QuestionAnswerAdvisor retrieves the top five chunks with a server-side region filter from the agent's identity, the system prompt says answer only from context and cite clauses, and the citations go back to the UI. The modular RAG advisor adds query rewriting and re-ranking when needed."

### Q4 [senior] How do you choose a chunking strategy?
tags: chunking, text-splitting, overlap, semantic-chunking, rag, retrieval-quality, profile-java-genai

**Start here: the concepts**
- **Chunk:** the unit you embed and retrieve. Too big: diluted embedding, wasted tokens. Too small: missing context.
- **Strategies:** fixed token size with overlap; recursive (split by paragraphs, then sentences); **structure-aware** (by headings, sections, table rows); semantic (split where meaning shifts); parent-child (retrieve small, return the bigger parent).

**The live scenario (functional requirement)**
*FR: "Answer questions over technical manuals with numbered procedures, warning boxes and spec tables."* With 1,000-token fixed chunks, answers mixed steps from different procedures and missed table values.

**What the interviewer is really checking**
That chunking is a retrieval-quality decision you evaluate, not a default.

**How I answer it**
1. **Respect structure:** split on headings and procedure boundaries; keep each numbered procedure whole if it fits; keep warnings attached to their step.
2. **Tables:** convert each row to a self-describing line ("Model X200 – max pressure – 12 bar") or keep small tables whole; plain text splitting destroys tables.
3. **Add context to every chunk:** document title + section path as a prefix ("Manual X200 > Maintenance > Replacing the filter"), which improves both embedding and the LLM's understanding.
4. **Size:** start around 300–600 tokens with 10–15% overlap for prose; tune.
5. **Parent-child:** embed small precise chunks for matching, but send the parent section to the LLM.
6. **Evaluate:** compare strategies on a golden question set with recall@k; pick by data.

**Trade-offs and what can go wrong**
- Overlap increases index size and duplicate hits.
- Semantic chunking costs extra embedding calls at ingest.
- Very small chunks raise the number of retrieved items needed for complete answers.

**How I'd monitor it**
Recall@k on the golden set per chunking version, average chunk tokens, duplicate-hit rate, answer completeness feedback.

**Follow-ups to expect**
- *Why prefix the section path?* -> Embeddings of a bare step ("Turn it clockwise") are ambiguous.
- *Scanned PDFs?* -> OCR first; layout-aware parsing for columns and tables.
- *Code or JSON documents?* -> Split by functions/objects, not tokens.

**60-second answer**
"Chunking decides what retrieval can find, so I treat it as a tuned, evaluated choice. For manuals I split on headings and procedure boundaries so a procedure stays whole with its warnings, turn table rows into self-describing lines, and prefix every chunk with document and section path. I start at 300 to 600 tokens with modest overlap, and use parent-child retrieval: match on small chunks, send the parent section to the model. Then I compare strategies on a golden question set by recall@k."

### Q5 [senior] Choose a vector database and explain how similarity search works.
tags: vector-database, pgvector, hnsw, cosine-similarity, ann, elasticsearch, profile-java-genai

**Start here: the concepts**
- **Similarity:** cosine similarity / dot product / Euclidean distance between embedding vectors.
- **ANN (approximate nearest neighbour) indexes:** **HNSW** (graph-based, fast and accurate, memory-heavy), IVF (clustering), plus quantisation to save memory.
- **Options:** pgvector (Postgres extension), Elasticsearch/OpenSearch (vector + keyword), Redis, MongoDB Atlas Vector Search, dedicated stores (Milvus, Qdrant, Weaviate, Pinecone), Chroma for prototypes.

**The live scenario (functional requirement)**
*FR: "Store 5 million chunks with tenant and permission metadata, hybrid keyword + semantic search, p95 retrieval under 150 ms, run in our cloud account."*

**What the interviewer is really checking**
Selection criteria grounded in requirements, and index trade-offs.

**How I answer it**
1. **Criteria:** scale (vectors and dimensions), filtering on metadata, hybrid search need, latency, ops model (managed vs self-run), existing skills, cost, data residency.
2. **Up to tens of millions with Postgres skills:** **pgvector** with HNSW: one database for metadata, ACLs and vectors, transactional updates, SQL filters.
3. **Hybrid search is central:** **OpenSearch/Elasticsearch**: BM25 keyword + kNN vectors in one query, mature filtering; good fit here.
4. **Hundreds of millions+ or advanced vector features:** a dedicated store (Milvus, Qdrant, Weaviate).
5. **Index tuning:** HNSW `m` and `ef_construction` at build, `ef_search` at query: recall vs latency; filtered search can hurt recall, so test with real filters.
6. **Dimensions and storage:** 5M × 1,024 dims × 4 bytes ≈ 20 GB raw floats before index overhead; quantisation (int8/binary) cuts it with small recall loss.
7. Spring AI's `VectorStore` abstraction keeps the app portable across most of these.

**Trade-offs and what can go wrong**
- Mixing vectors from different embedding models in one index breaks similarity.
- Restrictive metadata filters with HNSW can return too few results (post-filtering); prefer stores with efficient pre-filtering.
- A new specialised database adds ops burden; avoid it until needed.

**How I'd monitor it**
Query latency p95, recall on a benchmark set, index size and memory, ingestion throughput.

**Follow-ups to expect**
- *Cosine vs dot product?* -> Equivalent for normalised vectors; use what the embedding model recommends.
- *Exact search?* -> Brute force for small sets or for measuring ANN recall.
- *Re-indexing on model change?* -> New index version, backfill, switch alias.

**60-second answer**
"I choose by requirements: scale, metadata filtering, hybrid search, latency, ops model and residency. For 5 million chunks with hybrid keyword-plus-semantic search and permission filters, OpenSearch or Elasticsearch fits well: BM25 and kNN in one query with mature filters. If the team lives in Postgres and hybrid matters less, pgvector with HNSW keeps vectors, metadata and ACLs in one transactional store. I tune HNSW for recall against latency with real filters, budget memory, and keep the app portable through Spring AI's VectorStore."

### Q6 [senior] Retrieval quality is poor. How do you improve it?
tags: retrieval-quality, hybrid-search, reranking, query-rewriting, multi-query, metadata-filtering, profile-java-genai

**Start here: the concepts**
- **Hybrid search:** combine keyword (BM25: exact terms, codes, names) with vector (meaning) results, merged e.g. by reciprocal rank fusion.
- **Re-ranking:** a cross-encoder model scores (question, chunk) pairs precisely; retrieve 30-50 candidates, keep the best 5.
- **Query transformation:** rewrite vague or conversational questions; multi-query expansion; HyDE (embed a hypothetical answer).

**The live scenario (functional requirement)**
*FR: "Agents ask things like 'what's the excess for flood on plan GOLD-22?'"* The assistant often answers from the wrong plan or misses the clause.

**What the interviewer is really checking**
A diagnostic, layered approach rather than "use a bigger model".

**How I answer it**
1. **Diagnose first:** on a golden set, is the right chunk in the top 20 (retrieval problem) or retrieved but ignored (generation problem)?
2. **Exact identifiers** like `GOLD-22` are weak in pure vector search -> **hybrid search** with BM25.
3. **Metadata filters:** extract the plan code (with a small LLM call or regex) and filter `plan == 'GOLD-22'` before similarity.
4. **Query rewriting:** turn "and for fire?" into a standalone question using conversation history (Spring AI `RewriteQueryTransformer`/`CompressionQueryTransformer`).
5. **Re-rank** the top 30 candidates with a cross-encoder, send the best 4–5.
6. **Better chunks and metadata** (section path prefixes, Q4).
7. **Embedding model:** test a stronger or domain-suited model on the golden set; re-embed if it wins.

**Trade-offs and what can go wrong**
- Each step adds latency (a rewrite call ~300-800 ms, re-ranking ~50–200 ms); budget it.
- Over-filtering returns nothing; fall back to unfiltered search with a warning.
- Multi-query expansion multiplies retrieval cost.

**How I'd monitor it**
Recall@k and MRR on the golden set per change, re-ranker score distributions, "not found" rate, per-step latency.

**Follow-ups to expect**
- *What is reciprocal rank fusion?* -> Merging ranked lists by summing 1/(k + rank) per document.
- *HyDE?* -> Generate a hypothetical answer and embed it; helps when questions are short.
- *Where is the re-ranker hosted?* -> A small model via an API or self-hosted; it's cheap relative to the LLM.

**60-second answer**
"First I find out whether the right chunk is retrieved at all or retrieved and ignored, using a golden set. Plan codes like GOLD-22 are weak in vector search, so I add hybrid search with BM25 and extract the plan code into a metadata filter. Follow-up questions get rewritten into standalone ones, and I retrieve 30 candidates and re-rank with a cross-encoder to keep the best five. Better chunk prefixes and possibly a stronger embedding model come next. Each change is measured by recall@k and its latency cost."

### Q7 [senior] How do you reduce hallucinations and make answers verifiable?
tags: hallucination, grounding, citations, guardrails, faithfulness, abstention, profile-java-genai

**Start here: the concepts**
- **Hallucination:** content not supported by the sources or by fact, delivered confidently.
- **Grounding:** constraining the answer to provided context; **citations** make it checkable; **abstention** ("I don't know") is a valid outcome.

**The live scenario (functional requirement)**
*FR: "The banking assistant answers fee and eligibility questions; a wrong fee quoted to a customer is a compliance incident."*

**What the interviewer is really checking**
Layered controls, from retrieval to output checking to UX.

**How I answer it**
1. **Good retrieval** (Q6): most hallucinations come from missing or wrong context.
2. **Instructions:** "Use only the context. If the answer isn't there, say you don't know and offer a human agent. Cite the document id for every fact." Low temperature.
3. **Structured output** with `answer` + `citations[]` (doc id, quote), so citations are machine-checkable.
4. **Verify:** check each cited quote exists in the retrieved chunks; numbers (fees, percentages) in the answer must appear in cited text; otherwise block or regenerate. Optionally a second model call as a **faithfulness judge** for high-risk answers.
5. **Deterministic data via tools:** fees come from a pricing API tool call, not from text the model paraphrases.
6. **Abstain below a retrieval confidence threshold** (top similarity too low) without calling the LLM.
7. UX: show sources; disclaimers for regulated content; escalation path.

**Trade-offs and what can go wrong**
- Over-strict prompts produce too many "I don't know" answers; tune on evaluations.
- Judge models also err and add latency/cost; use them for high-risk categories.
- Citations can be fabricated unless verified against retrieved content.

**How I'd monitor it**
Faithfulness score on sampled production answers, citation verification failure rate, abstention rate, compliance escalations.

**Follow-ups to expect**
- *Can you eliminate hallucinations?* -> No; you reduce and detect them, and design the process for residual risk.
- *Spring AI support?* -> `FactCheckingEvaluator`/`RelevancyEvaluator` for evaluation; custom advisors for runtime checks.
- *Why tools for numbers?* -> Systems of record are authoritative; text can be outdated.

**60-second answer**
"You can't eliminate hallucinations, so I layer controls. Good retrieval first, since missing context causes most of them. A strict prompt: answer only from context, cite every fact, say 'I don't know' otherwise, at low temperature. Structured output with citations I verify in code: quotes must exist in the retrieved chunks and every fee must appear in cited text. Authoritative numbers come from a pricing tool call, low retrieval confidence abstains without calling the model, and sampled answers are scored for faithfulness."

### Q8 [senior] How do you evaluate a RAG system before and after go-live?
tags: evaluation, rag-evaluation, golden-dataset, llm-as-judge, recall-at-k, faithfulness, profile-java-genai

**Start here: the concepts**
- **Retrieval metrics:** recall@k (is the right chunk in the top k?), precision, MRR (rank of the first relevant hit).
- **Generation metrics:** faithfulness/groundedness (supported by context?), answer relevance, correctness vs a reference answer, format validity.
- **LLM-as-judge:** a model grades answers against criteria; needs calibration against human labels.

**The live scenario (functional requirement)**
*FR: "Before launching the policy assistant to 30,000 employees, prove it's accurate; after launch, catch regressions when prompts, models or documents change."*

**What the interviewer is really checking**
That you treat GenAI quality as a measurable, CI-gated property.

**How I answer it**
1. **Golden dataset:** 200–500 real questions (from HR tickets) with expected source documents and reference answers, reviewed by domain experts; include "not answerable" questions and tricky ones.
2. **Offline evaluation** script/test (JUnit-based is fine): for each question run retrieval -> compute recall@5, MRR; run generation -> judge faithfulness and correctness with an LLM judge (Spring AI's `RelevancyEvaluator`/`FactCheckingEvaluator`, or frameworks such as Ragas/DeepEval via a sidecar).
3. **Calibrate the judge** on 50 human-labelled answers; check agreement.
4. **Gate in CI:** any change to prompts, chunking, embedding or model must keep metrics above thresholds (e.g. recall@5 ≥ 0.9, faithfulness ≥ 0.95).
5. **Online:** thumbs up/down, escalation rate, sampled answers judged daily, A/B tests for prompt versions.
6. Add every production failure to the golden set.

**Trade-offs and what can go wrong**
- Small or synthetic-only golden sets give false confidence.
- Judges are biased (prefer longer answers, their own outputs); use rubrics and human spot checks.
- Evaluation costs tokens; run full suites nightly and a smaller smoke set per PR.

**How I'd monitor it**
Metric trends per release, judge-human agreement, online feedback rates, drift in retrieval scores.

**Follow-ups to expect**
- *How do you get ground truth?* -> Expert-labelled samples from real traffic, grown continuously.
- *Non-determinism in tests?* -> Thresholds over a set, multiple runs for borderline cases.
- *What about safety evals?* -> Red-team prompts (injection, toxic, PII) as a separate suite.

**60-second answer**
"I build a golden set of a few hundred real questions with expected sources and reference answers, reviewed by HR experts, including unanswerable ones. An evaluation suite measures retrieval with recall at 5 and MRR, and generation with faithfulness and correctness using an LLM judge calibrated against human labels. Any change to prompts, chunking, embeddings or model must pass thresholds in CI. After launch, feedback, escalations and daily judged samples catch drift, and every production failure joins the golden set."

### Q9 [mid] Get reliable structured output from an LLM in Java.
tags: structured-output, json-schema, beanoutputconverter, prompt-engineering, few-shot, spring-ai, profile-java-genai

**Start here: the concepts**
- **Structured output:** the model returns JSON matching a schema; many providers support schema-constrained decoding natively.
- **Spring AI:** `.call().entity(MyRecord.class)` (uses a `BeanOutputConverter` to add format instructions and parse; native structured output where the provider supports it).
- **LangChain4j:** AI Services returning a POJO/record type.

**The live scenario (functional requirement)**
*FR: "Extract invoice fields (supplier, invoice number, date, line items, total, currency) from uploaded invoices into the ERP; malformed data must never be posted."*

**What the interviewer is really checking**
Robust parsing, validation and fallbacks, not just "ask for JSON".

**How I answer it**
1. Define the target as a record with Bean Validation:

```java
record Invoice(@NotBlank String supplier, @NotBlank String number, LocalDate date,
               List<@Valid Line> lines, @Positive BigDecimal total, @Size(min=3,max=3) String currency) {}
Invoice inv = chatClient.prompt().system(EXTRACTION_RULES).user(text).call().entity(Invoice.class);
```

2. Prefer the provider's **native JSON-schema mode** when available; otherwise format instructions + parsing.
3. **Validate** the result (Bean Validation + business checks: line items sum to total).
4. On failure: one **repair retry** with the validation errors fed back; then route to a human review queue.
5. Low temperature; few-shot examples for tricky layouts; field descriptions in the schema.
6. Never trust extracted data for posting without validation; keep the source file linked for audit.

**Trade-offs and what can go wrong**
- Parsing failures from extra prose or truncated output (hit `max_tokens`).
- Hallucinated fields when the document lacks them; allow nulls and instruct "null if absent".
- Large documents may exceed context; chunk and merge carefully.

**How I'd monitor it**
Parse failure rate, validation failure rate per field, human-review queue size, extraction accuracy on a labelled sample.

**Follow-ups to expect**
- *Why not regex/OCR templates?* -> They break on new layouts; LLMs generalise, with validation as the safety net.
- *Enums?* -> Constrain values in the schema and validate.
- *Streaming structured output?* -> Parse after completion.

**60-second answer**
"I define the target as a validated record and call Spring AI's `.entity(Invoice.class)`, using the provider's native JSON-schema mode when available, at low temperature, with null allowed for missing fields. Then I validate in code: Bean Validation plus business checks like lines summing to the total. A failure gets one repair retry with the errors fed back, then goes to human review. Nothing reaches the ERP unvalidated, and I track parse and field-level failure rates."

### Q10 [senior] Implement conversation memory for a multi-turn assistant.
tags: chat-memory, conversation-history, summarization, context-window, redis, spring-ai, profile-java-genai

**Start here: the concepts**
- **The model is stateless:** memory = the application storing and resending prior messages.
- **Strategies:** sliding window (last N messages), token-budgeted window, summarisation of older turns, long-term memory (facts stored and retrieved like RAG).
- **Spring AI:** `ChatMemory` (`MessageWindowChatMemory`) with a repository (in-memory, JDBC, Cassandra, Neo4j...) and `MessageChatMemoryAdvisor`; conversation id per session.

**The live scenario (functional requirement)**
*FR: "A travel assistant handles 20-turn conversations ('change the hotel to one near the venue... and make it 2 nights'), across 6 pods, and must forget everything after 30 days for privacy."*

**What the interviewer is really checking**
Scalable state handling, token budgets and privacy.

**How I answer it**
1. **Store** messages per `conversationId` in a shared store (JDBC/Postgres or Redis), not in pod memory, so any pod can continue the chat.
2. Wire it:

```java
var memory = MessageWindowChatMemory.builder().chatMemoryRepository(jdbcRepo).maxMessages(20).build();
chatClient.prompt().user(msg)
   .advisors(MessageChatMemoryAdvisor.builder(memory).build(), a -> a.param(ChatMemory.CONVERSATION_ID, convId))
   .call().content();
```

3. **Token budget:** window by tokens, and **summarise** older turns into a running summary message when the history exceeds the budget.
4. **Structured state** beats raw history for task facts: keep the itinerary (dates, hotel, city) as a JSON state object in the prompt; the model doesn't have to re-derive it from 20 messages.
5. **Privacy:** TTL/retention job deleting conversations after 30 days; PII redaction before storage where possible; per-user isolation of conversation ids (validated against the authenticated user).
6. Reset/clear option for users.

**Trade-offs and what can go wrong**
- Full history grows cost per turn linearly; summaries lose detail.
- Trusting a client-supplied conversation id lets users read others' chats.
- Long-term "memories" can store wrong facts; let users view and delete them.

**How I'd monitor it**
Tokens per turn trend, conversation length distribution, summary frequency, retention job success.

**Follow-ups to expect**
- *Why not keep memory in the prompt on the client?* -> Tampering and size; the server owns it.
- *Vector-store memory?* -> Retrieve relevant past facts for long-lived assistants.
- *Multi-tenant isolation?* -> Tenant + user in the conversation key and checks on every access.

**60-second answer**
"The model is stateless, so memory is ours: messages stored per conversation id in Postgres or Redis so any of the six pods can continue, wired with Spring AI's chat memory and its advisor. I window by tokens and summarise older turns once history exceeds a budget, and I keep task state, like the itinerary, as a structured object in the prompt instead of making the model re-read 20 messages. Conversation ids are checked against the logged-in user, and a retention job deletes everything after 30 days."

### Q11 [architect] Choose and host models without lock-in: hosted APIs, cloud platforms or self-hosted open-weight models.
tags: model-selection, llm-hosting, open-weight-models, ai-gateway, vendor-lock-in, data-residency, profile-java-genai

**Start here: the concepts**
- **Hosted model APIs** (various providers): best frontier quality, pay per token, data leaves your account (contract terms matter).
- **Cloud AI platforms** (Azure OpenAI/AI Foundry, AWS Bedrock, Google Vertex AI): models inside your cloud agreement, regional deployment, enterprise controls.
- **Self-hosted open-weight models** (served with vLLM/TGI/Ollama): full data control, fixed GPU cost, more ops.
- **Portability layer:** Spring AI / LangChain4j abstractions plus an **AI gateway** (routing, quotas, fallback, logging).

**The live scenario (functional requirement)**
*FR: "A bank wants GenAI features: a public FAQ bot, an internal code assistant, and a document summariser for confidential loan files that must not leave the bank's environment; avoid dependence on one vendor."*

**What the interviewer is really checking**
Architecture for constraints (privacy, cost, quality) and portability.

**How I answer it**
1. **Classify data and tasks:** public FAQ (low sensitivity), internal code (medium), loan files (high, residency-bound).
2. **Loan summariser -> self-hosted open-weight model** inside the bank's VPC/on-prem GPUs, or a cloud platform deployment in the approved region with no data retention, per the risk team's decision.
3. **FAQ bot -> a cloud platform model** (cheap, mid-size model is enough).
4. **Code assistant -> a strong model** via the enterprise cloud agreement.
5. **AI gateway** in front of all: auth, per-team quotas, PII redaction, logging, routing rules (data classification -> allowed models), and fallback between providers.
6. Applications code only against Spring AI interfaces (`ChatClient`, `EmbeddingModel`); switching a model is configuration plus evaluation.
7. **Evaluate per task** on golden sets: quality, latency, cost; re-run when new models come out (every few months).

**Trade-offs and what can go wrong**
- Abstractions hide provider-specific features (prompt caching, special tools); allow escape hatches.
- Self-hosting needs GPU capacity planning and MLOps; utilisation drives cost.
- Prompts are often model-specific; switching needs re-tuning and re-evaluation.

**How I'd monitor it**
Cost per task per model, quality scores per model, gateway policy violations, provider availability.

**Follow-ups to expect**
- *Embedding model lock-in?* -> Switching means re-embedding the corpus; plan it as a migration.
- *Small vs large models?* -> Route simple tasks to small models; it's the biggest cost lever.
- *Contract points?* -> Data retention, training on your data, region, SLAs.

**60-second answer**
"I start from data classification. Confidential loan files go to a self-hosted open-weight model in the bank's environment, or a regional cloud deployment with no retention if risk approves. The public FAQ bot uses a cheaper cloud model, and the code assistant a stronger one under the enterprise agreement. Everything goes through an AI gateway that enforces which data class may use which model, redacts PII, applies quotas and falls back between providers. Apps code against Spring AI interfaces, so a switch is configuration plus re-evaluation."

### Q12 [senior] Cut the latency and cost of an LLM feature without hurting quality.
tags: llm-cost, latency, caching, semantic-cache, model-routing, token-optimization, profile-java-genai

**Start here: the concepts**
- **Cost** ≈ input tokens × price + output tokens × (higher) price. **Latency** ≈ time to first token + output tokens / generation speed.
- **Levers:** fewer tokens, smaller models, caching (prompt prefix caching, response caches), streaming, parallelism, batch APIs.

**The live scenario (functional requirement)**
*FR: "The support copilot costs $0.04 per answer and takes 9 s; target $0.01 and under 4 s, quality unchanged on the evaluation set."*

**What the interviewer is really checking**
Systematic optimisation with measurement.

**How I answer it**
1. **Measure the breakdown:** tokens per section (system prompt 1,500, history 3,000, retrieved context 6,000, output 600), latency per step (retrieval, rewrite call, generation).
2. **Trim context:** re-rank and send 4 chunks instead of 15 (6,000 -> 1,800 tokens); summarise history.
3. **Shorter outputs:** ask for concise answers, cap `max_tokens`; output tokens dominate latency.
4. **Route by difficulty:** a small model handles the ~70% of simple questions; the large model only for complex ones (a classifier or heuristic decides).
5. **Caching:** provider prompt caching for the stable system prompt prefix; exact-match response cache for frequent questions; semantic cache (embedding similarity > 0.95) only for non-personalised answers.
6. **Latency:** stream tokens; run retrieval and the query-rewrite in parallel where possible; skip the rewrite for standalone questions.
7. Re-run the evaluation set after each change; keep only changes that hold quality.

**Trade-offs and what can go wrong**
- Semantic caches can return a cached answer for a subtly different question; restrict scope and TTL.
- Routing mistakes send hard questions to small models; monitor quality per route.
- Aggressive context trimming loses needed facts.

**How I'd monitor it**
Cost per answer, tokens per section, p50/p95 latency and time to first token, cache hit rate, quality per route.

**Follow-ups to expect**
- *Batch APIs?* -> For offline jobs (summaries overnight), often far cheaper.
- *Speculative decoding / quantisation?* -> Relevant when self-hosting.
- *Precompute?* -> Summaries and embeddings at ingest time, not per query.

**60-second answer**
"I measure where tokens and time go, then cut. Re-ranking lets me send four chunks instead of fifteen, history gets summarised, answers are capped and concise since output tokens drive latency. A router sends the 70% of simple questions to a small model. Prompt caching covers the stable system prefix, an exact-match cache covers frequent questions, a semantic cache only covers non-personal answers. Streaming and parallel retrieval cut perceived latency. Every change has to hold the evaluation score, or it's reverted."

### Q13 [senior] Build multi-tenant, permission-aware RAG so users only see what they're allowed to.
tags: multi-tenancy, access-control, permission-aware-retrieval, metadata-filter, data-isolation, security, profile-java-genai

**Start here: the concepts**
- **Document-level ACLs:** each chunk carries tenant id and allowed groups/roles in metadata.
- **Filter at retrieval time:** the vector query includes a mandatory filter from the authenticated identity.
- **Isolation levels:** shared index with filters, index/collection per tenant, or database per tenant.

**The live scenario (functional requirement)**
*FR: "A SaaS knowledge assistant for 300 corporate customers; within each customer, HR documents are visible only to HR, and board minutes only to executives."*

**What the interviewer is really checking**
That the LLM must never see content the user can't access, enforced outside the model.

**How I answer it**
1. **Ingestion:** copy source permissions into chunk metadata: `tenantId`, `allowedGroups`, `classification`, `docId`.
2. **Query:** build the filter **server-side** from the JWT: `tenantId == :t AND allowedGroups IN (:userGroups)`, using the framework's filter builder (Spring AI `FilterExpressionBuilder`), never from request parameters.
3. **Isolation choice:** large or regulated tenants get a **separate index/collection**; small tenants share an index with mandatory tenant filters. Database-per-tenant for strict contracts.
4. **Permission changes:** subscribe to source-system ACL change events and update chunk metadata promptly; for highly sensitive data, re-check access against the source at query time for the final candidates.
5. **Defence in depth:** tests asserting cross-tenant queries return nothing; the prompt never includes other tenants' data; caches keyed by tenant + permission set.
6. **Tools** (MCP or function calls) also run with the user's permissions.

**Trade-offs and what can go wrong**
- Prompt instructions like "don't reveal HR data" are not access control.
- Stale ACLs after someone leaves HR: they still see HR docs until refreshed.
- Semantic caches shared across users leak answers.

**How I'd monitor it**
Cross-tenant test suite in CI, ACL sync lag, audit log of retrieved doc ids per answer, anomaly alerts on access patterns.

**Follow-ups to expect**
- *Why not filter after generation?* -> The model already saw the data; it can leak in the answer.
- *Group explosion?* -> Normalise to groups/roles; avoid per-user lists in metadata.
- *Audit?* -> Log which documents fed each answer.

**60-second answer**
"Access control happens before the model sees anything. Ingestion copies tenant and group permissions into each chunk's metadata; at query time the server builds a mandatory filter from the user's token, tenant plus their groups, never from request parameters. Big or regulated tenants get their own index, small ones share one with tenant filters. ACL changes flow in as events, and the most sensitive content is re-checked against the source. Caches are keyed by tenant and permissions, CI tests prove cross-tenant queries return nothing, and every answer logs its source documents."
