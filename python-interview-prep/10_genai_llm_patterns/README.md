# 10 — GenAI / LLM Patterns

Pure stdlib, mocked LLM calls — no API key needed. The point is the *shape* of these patterns
(prompt construction, the RAG pipeline, semantic caching), which is identical whether the LLM
call underneath is Bedrock, OpenAI, or Anthropic's API.

## Crib sheet

- **RAG (Retrieval-Augmented Generation)**: embed the query → similarity search a vector DB →
  inject the top-k retrieved chunks into the prompt → LLM answers grounded in that context, not
  just training data. Reduces hallucination on domain-specific questions without fine-tuning.
- **Prompt engineering basics**: zero-shot (just ask), few-shot (2-3 examples first), chain-of-
  thought ("think step by step"), ReAct (Thought → Action → Observation loop for tool-using
  agents). A production prompt should also explicitly say "if the answer isn't in the context,
  say so" — the single most effective anti-hallucination instruction.
- **RAG vs fine-tuning**: RAG for knowledge that changes often and needs citations (company docs,
  search); fine-tuning for teaching the model a *style* or *behavior pattern*, not new facts.
  Start with RAG; fine-tune only when the model needs to think/respond differently.
- **Semantic caching**: cache LLM responses by *meaning* (embedding similarity above a threshold),
  not exact string match — "What's the return policy?" and "How do I return an item?" should hit
  the same cached answer. Can cut LLM cost 90%+ on FAQ-shaped traffic.
- **Treat LLM calls like any other external dependency**: instrument latency/cost/error rate, add
  timeouts and circuit breakers (see `08_scaling_production_resilience`), and build a golden test
  set to catch answer-quality regressions in CI before they reach production.

## Files

| File | Topic |
|---|---|
| `01_prompt_engineering_examples.py` | zero-shot vs few-shot vs chain-of-thought prompt construction |
| `02_rag_pipeline_concept.py` | a runnable mini-RAG: keyword "retrieval" + mocked LLM, showing the full pipeline shape |
| `03_semantic_caching_concept.py` | exact-match cache vs a simple similarity-based cache (Jaccard over words, no embeddings needed) |

## Exercise

Swap `02_rag_pipeline_concept.py`'s keyword-overlap retriever for a real embedding-based one
(e.g. using any small sentence-transformer, or even just TF-IDF cosine similarity via
`scikit-learn`) and confirm the rest of the pipeline (prompt assembly, mocked generation, source
citation) needs zero changes — that decoupling is the actual architectural point of RAG.
