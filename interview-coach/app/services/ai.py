"""The AI coach: one prompt builder, two interchangeable providers behind ``stream_answer()``.

- **claude**: streams from the Claude API (``anthropic`` SDK). The system prompt is the stack persona
  plus the topic's skill pack — stable per topic, so it is marked for prompt caching.
- **mock**:   offline and deterministic, built from the question bank itself (closest stored answer,
  keyword-coverage scorecard). The whole app is usable without a key.

``AI_MODE=auto`` (default) uses claude when ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN is set;
``claude`` or ``mock`` force one (``claude`` also works with an ``ant auth login`` profile).
"""
import asyncio
import os
import re

from .. import config
from . import bank, retrieve

DIMENSIONS = [("scenario", "Scenario & context"), ("depth", "Technical depth"),
              ("tradeoffs", "Trade-offs & failure modes"), ("monitoring", "Monitoring & operations"),
              ("clarity", "Clarity & structure")]

SCORECARD_FORMAT = """Reply in exactly this Markdown structure:

### Scorecard
| Dimension | Score (1-5) | Why |
|---|---|---|
""" + "\n".join(f"| {label} | n | one line |" for _, label in DIMENSIONS) + """

### What you did well
- 1-3 bullets

### What was missing
- the most important gaps first, each with one line on how to say it

### A stronger answer (60 seconds)
A paragraph the candidate could say out loud.

### Follow-up question
One realistic follow-up the interviewer would ask next.

End with this exact final line (numbers only):
SCORES: scenario=n depth=n tradeoffs=n monitoring=n clarity=n"""

BANK_FORMAT = """Write exactly ONE new interview question in this Markdown format and nothing else:

### Q0 [{level}] <the question, as an interviewer would ask it>
tags: <4-6 lowercase comma-separated tags>

**The live scenario**
<a concrete production situation with numbers>

**What the interviewer is really checking**
<1-2 sentences>

**How I answer it**
<numbered steps, each a decision plus its reason>

**Trade-offs and what can go wrong**
<bullets>

**How I'd monitor it**
<metrics, log searches, alerts>

**Follow-ups to expect**
- *<follow-up question>* -> <one-line answer>
- *<follow-up question>* -> <one-line answer>

**60-second answer**
<a paragraph to say out loud>

Optionally add a final **Minimal config** section with at most 5 lines in a fenced block."""


def mode() -> str:
    wanted = config.AI_MODE
    has_key = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))
    if wanted == "mock" or (wanted == "auto" and not has_key):
        return "mock"
    return "claude"


def status() -> dict:
    m = mode()
    return {"provider": m, "model": config.ANTHROPIC_MODEL if m == "claude" else "offline mock",
            "effort": config.AI_EFFORT}


# ---------------------------------------------------------------- prompt building

def system_prompt(stack, topic) -> str:
    """Persona + skill pack. Kept byte-stable per (stack, topic) so the API can cache it."""
    if topic is not None:
        return f"{stack.persona}\n\n## Topic: {topic.title}\n{topic.summary}\n\n{topic.instructions}"
    topics = "\n".join(f"- {t.title}: {t.summary}" for t in stack.topics)
    return f"{stack.persona}\n\n## Topics this coach covers\n{topics}"


def _qa_block(q: dict, limit: int = 3500) -> str:
    return f'<reference id="{q["id"]}" kind="{q["kind"]}" level="{q["level"]}">\n' \
           f'Q: {q["title"]}\n{q["body"][:limit]}\n</reference>'


def user_prompt(req: dict, ctx: dict) -> str:
    m, level = req["mode"], req.get("level") or "senior"
    q, refs = ctx.get("question"), ctx.get("refs", [])
    ref_text = "\n\n".join(_qa_block(r) for r in refs)
    if m == "ask":
        return (f"Candidate level: {level}\n<question>{req['text']}</question>\n\n"
                f"<reference_material>\n{ref_text or '(none found)'}\n</reference_material>\n\n"
                "Answer the question in the scenario-first structure. Use the reference material for consistency "
                "with what the candidate has studied, but correct it if anything there is wrong or outdated.")
    if m == "explain":
        return (f"Candidate level: {q['level']}\n<question>{q['title']}</question>\n"
                f"<stored_answer>\n{q['body'][:8000]}\n</stored_answer>\n\n"
                "The candidate has read the stored answer and wants to go deeper. Do NOT repeat it. Give: "
                "(1) a second, different live scenario where this matters, (2) the subtle edge cases and the mistakes "
                "candidates make, (3) the three hardest follow-ups a tough interviewer would ask, each with a strong "
                "answer, (4) a sharper 60-second answer.")
    if m == "interview":
        reference = f"<reference_answer>\n{q['body'][:6000]}\n</reference_answer>\n" if q else ""
        question = q["title"] if q else req.get("text", "")
        return (f"You are now the INTERVIEWER grading a candidate at level: {level}.\n"
                f"<question>{question}</question>\n{reference}"
                f"<candidate_answer>\n{req.get('answer', '')}\n</candidate_answer>\n\n"
                "Grade fairly for the level: a fresher is not expected to discuss org-wide trade-offs, an architect is. "
                "Be specific and encouraging but honest. If the answer is empty or off-topic, score 1s and say so.\n\n"
                + SCORECARD_FORMAT)
    if m == "improve":
        question = q["title"] if q else req.get("text", "")
        return (f"Candidate level: {level}\n<question>{question}</question>\n"
                f"<candidate_answer>\n{req.get('answer', '')}\n</candidate_answer>\n\n"
                "Rewrite the candidate's answer the way you would say it in the interview, keeping their real "
                "experience but adding a live scenario, structure, trade-offs and monitoring. Then add a section "
                "'### What changed and why' with 3-6 bullets.")
    if m == "generate":
        existing = "\n".join(f"- {t}" for t in ctx.get("existing_titles", [])[:80])
        hint = req.get("text") or "any important area not yet covered"
        return (f"Focus: {hint}\nLevel: {req.get('level') or 'senior'}\n\n"
                f"Questions that already exist for this topic (do not duplicate them):\n{existing}\n\n"
                + BANK_FORMAT.format(level=req.get("level") or "senior"))
    if m == "jd":
        topics = "\n".join(f"- {t['id']}: {t['title']}" for t in ctx.get("topics", []))
        return (f"<job_description>\n{req.get('text', '')[:12000]}\n</job_description>\n\n"
                f"The coach has these topic areas:\n{topics}\n\n"
                "Produce a study plan for this job description with these sections:\n"
                "### What this role will test\n(skills ranked by weight, with the evidence from the JD)\n"
                "### Study plan\n(ordered topic areas from the list above, with what to focus on in each)\n"
                "### 12 questions you are likely to be asked\n(numbered, scenario-style, mixed levels)\n"
                "### Stories to prepare\n(3-4 production stories the candidate should have ready, and what each must show)")
    raise ValueError(f"unknown mode {m!r}")


# ---------------------------------------------------------------- mock provider

def _key_terms(q: dict) -> list[str]:
    """Terms a good answer to ``q`` should mention: tags, bold phrases and code-ish tokens."""
    terms = {t.replace("-", " ") for t in q.get("tags", [])}
    body = q.get("body", "")
    terms |= {m.strip().lower() for m in re.findall(r"`([^`]{3,40})`", body)}
    terms |= {m.strip().lower() for m in re.findall(r"\*\*([^*]{3,40})\*\*", body)}
    noise = {s["label"].lower() for s in q.get("sections", [])}
    return sorted(t for t in terms if t and t not in noise and len(t) < 40)[:25]


def score_answer(q: dict | None, answer: str) -> dict:
    a = answer.lower()
    words = len(answer.split())
    terms = _key_terms(q) if q else []
    hit = [t for t in terms if t in a]
    missing = [t for t in terms if t not in a]
    coverage = len(hit) / len(terms) if terms else min(1.0, words / 150)

    def clamp(x):
        return max(1, min(5, round(x)))
    scores = {
        "scenario": clamp(1 + 2 * bool(re.search(r"\d", answer)) + 2 * bool(
            re.search(r"\b(we|our|i|production|incident|customer|when)\b", a))),
        "depth": clamp(1 + 4 * coverage),
        "tradeoffs": clamp(1 + 2 * bool(re.search(r"trade-?off|downside|risk|however|but\b|cost", a)) + coverage * 2),
        "monitoring": clamp(1 + 3 * bool(re.search(r"monitor|metric|alert|dashboard|splunk|log|lag", a)) + coverage),
        "clarity": clamp(1 + (words >= 60) + (words >= 120) + bool(re.search(r"(^|\n)\s*(\d+[.)]|-)\s", answer))
                         + (words <= 450)),
    }
    if words < 15:
        scores = {k: 1 for k in scores}
    return {"scores": scores, "hit": hit, "missing": missing, "words": words}


def _scores_line(scores: dict) -> str:
    return "SCORES: " + " ".join(f"{k}={scores[k]}" for k, _ in DIMENSIONS)


MOCK_NOTE = "\n\n> Offline mock coach: built from your question bank. Set `ANTHROPIC_API_KEY` for the real AI coach."


def mock_answer(req: dict, ctx: dict) -> str:
    m, q, refs = req["mode"], ctx.get("question"), ctx.get("refs", [])
    if m == "ask":
        if not refs:
            return "No stored question matches those words yet. Try different keywords, or pick a topic first." + MOCK_NOTE
        best = refs[0]
        others = "\n".join(f"- {r['title']} *({r['kind']}, {r['level']})*" for r in refs[1:])
        return (f"**Closest answer in your bank:** {best['title']}\n\n{best['body']}\n\n"
                + (f"**Also related:**\n{others}" if others else "") + MOCK_NOTE)
    if m == "explain":
        fu = bank.followups(q)
        extra = "\n".join(f"- {f}" for f in fu) or "- What breaks first at 10x the load?\n- How would you monitor it?"
        return (f"**Going deeper on:** {q['title']}\n\nRe-read the stored answer and practise these follow-ups out loud:\n\n"
                f"{extra}\n\nThen try **Practice** mode on this question to get a scorecard." + MOCK_NOTE)
    if m in ("interview", "improve"):
        r = score_answer(q, req.get("answer", ""))
        spoken = bank.section(q, "spoken") if q else ""
        if m == "improve":
            return ("### Terms your answer covered\n" + (", ".join(r["hit"]) or "none of the key terms yet") +
                    "\n\n### Add these\n" + ("\n".join(f"- {t}" for t in r["missing"][:10]) or "- nothing obvious") +
                    (f"\n\n### Model 60-second answer\n{spoken}" if spoken else "") + MOCK_NOTE)
        rows = "\n".join(f"| {label} | {r['scores'][k]} | heuristic |" for k, label in DIMENSIONS)
        fu = (bank.followups(q) or ["How would you monitor this in production?"])[0] if q else \
            "How would you monitor this in production?"
        return ("### Scorecard\n| Dimension | Score (1-5) | Why |\n|---|---|---|\n" + rows +
                f"\n\n### What you did well\n- Covered: {', '.join(r['hit'][:8]) or 'start with a concrete scenario'}"
                f"\n\n### What was missing\n" + ("\n".join(f"- {t}" for t in r["missing"][:8]) or "- nothing major") +
                (f"\n\n### A stronger answer (60 seconds)\n{spoken}" if spoken else "") +
                f"\n\n### Follow-up question\n{fu}" + MOCK_NOTE + "\n\n" + _scores_line(r["scores"]))
    if m == "generate":
        level = req.get("level") or "senior"
        hint = req.get("text") or "a production scenario"
        return BANK_FORMAT.split("\n\n", 1)[1].format(level=level).replace(
            "<the question, as an interviewer would ask it>", f"How would you handle {hint}?") + \
            "\n\n> Offline mock: this is the empty template. With an API key the coach drafts the full answer."
    if m == "jd":
        ranked = ctx.get("jd_topics", [])
        plan = "\n".join(f"{i}. **{t['title']}** — {t['hits']} matching terms" for i, t in enumerate(ranked, 1))
        return ("### Study plan (keyword match against your topics)\n" + (plan or "No topic matched; paste more of the JD.")
                + "\n\nOpen each topic, filter by your level, and use **Practice** mode on its scenario questions first."
                + MOCK_NOTE)
    return "Unknown mode."


async def _stream_mock(req, ctx):
    text = mock_answer(req, ctx)
    for i in range(0, len(text), 48):
        yield text[i:i + 48]
        await asyncio.sleep(0.008)


# ---------------------------------------------------------------- claude provider

async def _stream_claude(req, ctx):
    try:
        import anthropic
    except ImportError:
        yield "> The `anthropic` package is not installed (`pip install anthropic`); showing the offline answer.\n\n"
        async for chunk in _stream_mock(req, ctx):
            yield chunk
        return
    client = anthropic.AsyncAnthropic()
    params = dict(
        model=config.ANTHROPIC_MODEL, max_tokens=config.AI_MAX_TOKENS,
        system=[{"type": "text", "text": ctx["system"], "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_prompt(req, ctx)}],
        output_config={"effort": config.AI_EFFORT},
    )
    try:
        if config.AI_FALLBACKS:
            stream_cm = client.beta.messages.stream(betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                                                    **params)
        else:
            stream_cm = client.messages.stream(**params)
        async with stream_cm as stream:
            async for text in stream.text_stream:
                yield text
            final = await stream.get_final_message()
        if final.stop_reason == "refusal":
            yield "\n\n> The model declined to answer this request. Try rephrasing the question."
        elif final.stop_reason == "max_tokens":
            yield "\n\n> (answer truncated at the token limit)"
    except anthropic.AuthenticationError:
        yield "\n\n> AI error: the API key was rejected. Check `ANTHROPIC_API_KEY`, or set `AI_MODE=mock`."
    except anthropic.RateLimitError:
        yield "\n\n> AI error: rate limited by the API. Wait a moment and try again."
    except anthropic.APIStatusError as e:
        yield f"\n\n> AI error {e.status_code}: {e.message}"
    except anthropic.APIConnectionError:
        yield "\n\n> AI error: could not reach the API (network). The offline mock still works with `AI_MODE=mock`."


async def stream_answer(req: dict, ctx: dict):
    provider = _stream_claude if mode() == "claude" else _stream_mock
    async for chunk in provider(req, ctx):
        yield chunk


def build_context(lib, req: dict) -> dict:
    """Everything a prompt needs, resolved from the library (shared by both providers)."""
    stack = lib.stack(req["stack"])
    if stack is None:
        raise ValueError("unknown stack")
    q = lib.question(req["question_id"]) if req.get("question_id") else None
    topic_id = req.get("topic") or (q["topic"] if q else "")
    topic = lib.topic(stack.id, topic_id) if topic_id else None
    ctx = {"question": q, "system": system_prompt(stack, topic), "refs": []}
    if req["mode"] == "ask":
        pool = lib.questions(stack.id, topic.id if topic else None)
        ctx["refs"] = [r for _, r in retrieve.search(pool, req.get("text", ""), k=3, level=req.get("level", ""))]
    elif req["mode"] == "generate" and topic:
        ctx["existing_titles"] = [x["title"] for x in topic.questions if x["kind"] == "scenario"] or \
                                 [x["title"] for x in topic.questions]
    elif req["mode"] == "jd":
        ctx["topics"] = [{"id": t.id, "title": t.title} for t in stack.topics]
        ctx["jd_topics"] = jd_topics(stack, req.get("text", ""))
    return ctx


def jd_topics(stack, text: str) -> list[dict]:
    """Deterministic topic ranking for a job description (used by the mock and shown alongside the AI plan)."""
    from .library import _kw_hits
    out = [{"id": t.id, "title": t.title, "hits": _kw_hits(text, t.keywords)} for t in stack.topics if t.keywords]
    return sorted((t for t in out if t["hits"]), key=lambda t: -t["hits"])
