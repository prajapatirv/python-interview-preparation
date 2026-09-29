"""
Prompt engineering techniques: zero-shot, few-shot, chain-of-thought, and a production-shaped
grounded-answer prompt. No API key needed -- prints the assembled prompts so you can see exactly
what would be sent to a real model.

Run me: python 01_prompt_engineering_examples.py
"""


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- zero-shot
section("zero-shot — just ask, no examples")
zero_shot = "Classify the sentiment of this review as positive, negative, or neutral: 'The battery life is disappointing.'"
print(zero_shot)


# ---------------------------------------------------------------- few-shot
section("few-shot — 2-3 examples steer the model's output FORMAT and reasoning")
few_shot = """Classify the sentiment as positive, negative, or neutral.

Review: "Fast shipping, exactly as described."
Sentiment: positive

Review: "Arrived broken, packaging was flimsy."
Sentiment: negative

Review: "The battery life is disappointing."
Sentiment:"""
print(few_shot)


# ---------------------------------------------------------------- chain-of-thought
section("chain-of-thought — asking the model to reason step by step before answering")
cot = """A store had 120 items. They sold 45% on Monday and 30 more on Tuesday.
How many items are left? Think step by step, then give the final answer on its own line."""
print(cot)


# ---------------------------------------------------------------- production-grade grounded prompt
section("production pattern: grounded answer + explicit anti-hallucination instruction + citation")


def build_grounded_prompt(user_question: str, context_docs: list[str], user_role: str = "customer") -> str:
    context = "\n\n".join(f"[Source {i + 1}] {doc}" for i, doc in enumerate(context_docs[:3]))
    return f"""You are a helpful assistant for {user_role} users.

Answer ONLY based on the provided context below. If the answer is not in the context,
say "I don't have information about this" -- never guess or use outside knowledge.

Context:
{context}

Question: {user_question}

Instructions:
- Be concise and direct
- Cite the source number [Source N] you used
- Never make up facts not present in the context
"""


docs = [
    "Our return window is 30 days from the delivery date, unopened or defective items only.",
    "Shipping is free on orders over $50; otherwise a flat $5.99 fee applies.",
]
prompt = build_grounded_prompt("How long do I have to return an item?", docs)
print(prompt)

print(
    "This is the single instruction with the biggest measurable impact on hallucination rate in "
    "practice: explicitly telling the model it's ALLOWED to say 'I don't know' rather than "
    "implicitly pressuring it to always produce a confident-sounding answer."
)

# EXERCISE: rewrite build_grounded_prompt as a few-shot version that includes ONE example of a
# question answered correctly from context, and one example of a question correctly declined
# because the context didn't cover it. Argue whether the extra tokens are worth it for your
# use case (they usually are for high-stakes domains like medical/legal/financial).
