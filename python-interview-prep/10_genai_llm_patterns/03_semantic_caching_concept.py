"""
Semantic caching: cache LLM responses by MEANING, not exact string match. Uses Jaccard word
overlap as a cheap, honest stand-in for embedding cosine similarity -- no API key or embedding
model needed to see the concept work. Caveat worth saying out loud: Jaccard only catches
paraphrases that still share several literal words ("how many days" vs "how long"-style true
rewordings would slip past it) -- that gap is EXACTLY why real systems use embeddings, which
capture meaning rather than surface word overlap.

Run me: python 03_semantic_caching_concept.py
"""


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def similarity(a: str, b: str) -> float:
    words_a, words_b = set(a.lower().split()), set(b.lower().split())
    union = words_a | words_b
    if not union:
        return 0.0
    return len(words_a & words_b) / len(union)


llm_call_count = {"n": 0}


def real_llm_call(question: str) -> str:
    llm_call_count["n"] += 1
    return f"[generated answer #{llm_call_count['n']} for: {question}]"


# ---------------------------------------------------------------- exact-match cache (misses paraphrases)
section("exact-match cache: a paraphrased question is a cache MISS, wasting an LLM call")
exact_cache: dict[str, str] = {}


def ask_exact_cache(question: str) -> str:
    if question in exact_cache:
        return exact_cache[question] + "  (cache HIT)"
    answer = real_llm_call(question)
    exact_cache[question] = answer
    return answer + "  (cache MISS -- real LLM call made)"


print(ask_exact_cache("How long do I have to return an order?"))
print(ask_exact_cache("How many days can I return an order?"))  # same MEANING, different string -> miss
print(f"total real LLM calls so far: {llm_call_count['n']}")


# ---------------------------------------------------------------- semantic cache (catches paraphrases)
section("semantic cache: a paraphrase above the similarity threshold is a cache HIT")
llm_call_count["n"] = 0
semantic_cache: list[tuple[str, str]] = []  # (question, answer) pairs
SIMILARITY_THRESHOLD = 0.3  # tune per use case; real systems use embedding cosine similarity here


def ask_semantic_cache(question: str) -> str:
    for cached_question, cached_answer in semantic_cache:
        score = similarity(question, cached_question)
        if score >= SIMILARITY_THRESHOLD:
            return cached_answer + f"  (cache HIT, similarity={score:.2f} vs '{cached_question}')"

    answer = real_llm_call(question)
    semantic_cache.append((question, answer))
    return answer + "  (cache MISS -- real LLM call made)"


print(ask_semantic_cache("How long do I have to return an order?"))
print(ask_semantic_cache("How many days can I return an order?"))
print(f"total real LLM calls so far: {llm_call_count['n']}")

print("\n(a completely unrelated question should still miss)")
print(ask_semantic_cache("Do you offer gift wrapping?"))
print(f"total real LLM calls: {llm_call_count['n']}")

# EXPERIMENT: lower SIMILARITY_THRESHOLD to 0.1 and rerun -- unrelated questions start
# incorrectly hitting the cache. This is the real production trade-off: too high a threshold
# wastes LLM calls on true paraphrases; too low and you serve a wrong cached answer.
