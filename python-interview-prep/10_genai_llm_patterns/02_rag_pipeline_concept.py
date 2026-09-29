"""
A runnable mini-RAG pipeline: keyword-overlap "retrieval" (stand-in for a real vector DB) +
a mocked LLM "generation" step. The point isn't the retrieval algorithm's sophistication -- it's
the PIPELINE SHAPE, which is identical whether retrieval is keyword overlap, TF-IDF, or real
embeddings against Pinecone/OpenSearch/pgvector.

Run me: python 02_rag_pipeline_concept.py
"""
import re


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- the "knowledge base"
KNOWLEDGE_BASE = [
    {"id": "doc-1", "text": "Our return window is 30 days from delivery, for unopened or defective items."},
    {"id": "doc-2", "text": "Shipping is free on orders over $50; otherwise a flat $5.99 fee applies."},
    {"id": "doc-3", "text": "Gift cards do not expire and cannot be redeemed for cash."},
    {"id": "doc-4", "text": "We ship to all 50 US states; international shipping is not currently supported."},
]


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z']+", text.lower()))


# ---------------------------------------------------------------- retrieval step
def retrieve(query: str, k: int = 2) -> list[dict]:
    """Stands in for: embed(query) -> vector_db.similarity_search(embedding, k). Real systems use
    cosine similarity over dense embeddings; this uses Jaccard word overlap, which is enough to
    demonstrate the pipeline shape without needing an embedding model or API key."""
    query_words = tokenize(query)
    scored = []
    for doc in KNOWLEDGE_BASE:
        doc_words = tokenize(doc["text"])
        overlap = len(query_words & doc_words)
        union = len(query_words | doc_words)
        score = overlap / union if union else 0
        scored.append((score, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for score, doc in scored[:k] if score > 0]


# ---------------------------------------------------------------- prompt assembly (same as file 01)
def build_prompt(question: str, retrieved_docs: list[dict]) -> str:
    context = "\n".join(f"[{d['id']}] {d['text']}" for d in retrieved_docs)
    return (
        "Answer ONLY using the context below. If it doesn't cover the question, say so.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
    )


# ---------------------------------------------------------------- mocked "generation" step
def mock_llm_generate(prompt: str, retrieved_docs: list[dict]) -> str:
    """A real system calls Bedrock/OpenAI/Anthropic here. This mock just extracts the most
    relevant retrieved sentence so the demo is deterministic and needs no API key -- the CONTRACT
    (prompt in, grounded answer + sources out) is what matters for this exercise."""
    if not retrieved_docs:
        return "I don't have information about this."
    return retrieved_docs[0]["text"]


# ---------------------------------------------------------------- the full pipeline
def answer_question(question: str) -> dict:
    retrieved = retrieve(question, k=2)
    prompt = build_prompt(question, retrieved)
    answer = mock_llm_generate(prompt, retrieved)
    return {
        "question": question,
        "answer": answer,
        "sources": [d["id"] for d in retrieved],
        "prompt_sent_to_llm": prompt,
    }


# ---------------------------------------------------------------- demo
section("query covered by the knowledge base")
result = answer_question("How many days do I have to return something?")
print("answer :", result["answer"])
print("sources:", result["sources"])

section("query NOT covered by the knowledge base -- the model should decline, not hallucinate")
result2 = answer_question("What's your policy on price matching a competitor?")
print("answer :", result2["answer"])
print("sources:", result2["sources"], "(empty -> nothing relevant was retrieved)")

section("the exact prompt that was assembled and would be sent to a real LLM")
print(result["prompt_sent_to_llm"])

# EXPERIMENT: add a 5th document to KNOWLEDGE_BASE about price matching, rerun the second query,
# and watch retrieve() find it and mock_llm_generate() answer from it instead of declining.
