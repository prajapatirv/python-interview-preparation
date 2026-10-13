"""Check my answer: fact-check a learner's answer claim by claim, grounded on the question bank.

``check_answer()`` returns the structured result described in docs/SELF_IMPROVING_DESIGN.md section 4::

    {"claims": [{"text", "verdict", "correction", "source"}], "missing": [...], "scores": {...},
     "improved_answer": str, "follow_up": str, "provider": "claude" | "mock"}

Two providers behind one function, like ``ai.py``: Claude (one non-streaming call that must answer in
JSON) and an offline mock built from the bank. The mock can say *correct* or *unverifiable* but never
*incorrect* - it has no way to know - and the result says so.
"""
import hashlib
import json
import re

from .. import config
from . import ai, bank, retrieve

VERDICTS = ("correct", "partially_correct", "incorrect", "outdated", "unverifiable")
DIM_KEYS = [k for k, _ in ai.DIMENSIONS]

CHECK_FORMAT = """Fact-check the candidate's answer. Split it into its individual factual claims (quote or
tightly paraphrase each one), judge each, then score it. Reply with ONE JSON object and nothing else:

{
  "claims": [{"text": "<claim from the answer>",
              "verdict": "correct|partially_correct|incorrect|outdated|unverifiable",
              "correction": "<what is right instead; empty when correct>",
              "source": "<id of the reference that supports the verdict, or 'knowledge'>"}],
  "missing": ["<important point the answer left out, most important first>"],
  "scores": {"scenario": 1-5, "depth": 1-5, "tradeoffs": 1-5, "monitoring": 1-5, "clarity": 1-5},
  "improved_answer": "<the candidate's answer rewritten for a spoken interview, keeping their real experience>",
  "follow_up": "<one realistic follow-up question>"
}

Rules: use "unverifiable" rather than guessing; use "outdated" only for facts that were true for an older
version; never invent a source id; opinions and personal experience are not claims."""


# Changes whenever the checker prompt changes, so attempts and eval runs can be compared per version.
PROMPT_VERSION = hashlib.sha1(CHECK_FORMAT.encode("utf-8")).hexdigest()[:8]


def _refs(lib, stack_id: str, q: dict | None, answer: str, level: str) -> list[dict]:
    """The question's own answer first, then the closest other bank entries."""
    out = [q] if q else []
    pool = [x for x in lib.questions(stack_id, q["topic"]) if x["id"] != q["id"]] if q else \
        lib.questions(stack_id)
    out += [r for _, r in retrieve.search(pool, ((q["title"] if q else "") + " " + answer)[:1500], k=2, level=level)]
    return out


def prompt(q: dict | None, question_text: str, answer: str, level: str, refs: list[dict]) -> str:
    ref_text = "\n\n".join(ai._qa_block(r, 3000) for r in refs) or "(no reference material)"
    return (f"Candidate level: {level}\n<question>{q['title'] if q else question_text}</question>\n"
            f"<reference_material>\n{ref_text}\n</reference_material>\n"
            f"<candidate_answer>\n{answer}\n</candidate_answer>\n\n"
            "Judge against the reference material, but trust it only as far as it is correct; if it is itself "
            "wrong or outdated, say so with source 'knowledge'. Grade for the candidate's level.\n\n" + CHECK_FORMAT)


def normalise(raw: dict, valid_sources: set[str]) -> dict:
    """Coerce model output into the schema; never trust it to be well-formed."""
    claims = []
    for c in raw.get("claims") or []:
        if not isinstance(c, dict) or not str(c.get("text", "")).strip():
            continue
        verdict = c.get("verdict") if c.get("verdict") in VERDICTS else "unverifiable"
        src = str(c.get("source", "")) if str(c.get("source", "")) in valid_sources else "knowledge"
        claims.append({"text": str(c["text"]).strip(), "verdict": verdict,
                       "correction": str(c.get("correction", "")).strip(), "source": src})
    raw_scores = raw.get("scores") if isinstance(raw.get("scores"), dict) else {}
    scores = {}
    for k in DIM_KEYS:
        try:
            scores[k] = max(1, min(5, int(round(float(raw_scores.get(k, 1))))))
        except (TypeError, ValueError):
            scores[k] = 1
    return {"claims": claims, "scores": scores,
            "missing": [str(m).strip() for m in (raw.get("missing") or []) if str(m).strip()][:10],
            "improved_answer": str(raw.get("improved_answer", "")).strip(),
            "follow_up": str(raw.get("follow_up", "")).strip()}


def parse_json(text: str) -> dict:
    """Extract the first JSON object from a reply, tolerating code fences and a preamble."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the reply")
    return json.loads(text[start:end + 1])


# ---------------------------------------------------------------- mock provider

def _sentences(answer: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", answer)
    return [p.strip(" -*\t") for p in parts if len(p.split()) >= 4]


def mock_check(q: dict | None, answer: str, refs: list[dict]) -> dict:
    scored = ai.score_answer(q, answer)
    terms = {t: r["id"] for r in refs for t in ai._key_terms(r)}
    claims = []
    for s in _sentences(answer)[:12]:
        low = s.lower()
        hit = [t for t in terms if t in low]
        if hit:
            claims.append({"text": s, "verdict": "correct", "source": terms[hit[0]],
                           "correction": f"Matches the bank on: {', '.join(hit[:3])}."})
        else:
            claims.append({"text": s, "verdict": "unverifiable", "source": "knowledge",
                           "correction": "Not found in your bank; the offline mock cannot verify it."})
    spoken = bank.section(q, "spoken") if q else ""
    fu = (bank.followups(q) or [""])[0] if q else ""
    return {"claims": claims, "scores": scored["scores"], "missing": scored["missing"][:8],
            "improved_answer": spoken, "follow_up": fu or "How would you monitor this in production?"}


# ---------------------------------------------------------------- claude provider

async def _claude_check(system: str, user: str) -> dict:
    import anthropic
    client = anthropic.AsyncAnthropic()
    msg = await client.messages.create(
        model=config.ANTHROPIC_MODEL, max_tokens=config.AI_MAX_TOKENS,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_config={"effort": config.AI_EFFORT})
    if msg.stop_reason == "refusal":
        raise ValueError("the model declined to check this answer")
    return parse_json("".join(b.text for b in msg.content if b.type == "text"))


async def check_answer(lib, req: dict) -> dict:
    stack = lib.stack(req["stack"])
    if stack is None:
        raise ValueError("unknown stack")
    q = lib.question(req["question_id"]) if req.get("question_id") else None
    if q is None and not req.get("text", "").strip():
        raise ValueError("give a question_id or the question text")
    level = req.get("level") or (q["level"] if q else "senior")
    answer = req["answer"].strip()
    refs = _refs(lib, stack.id, q, answer, level)
    note = ""
    provider = ai.mode()
    result = None
    if provider == "claude":
        try:
            topic = lib.topic(stack.id, q["topic"]) if q else None
            raw = await _claude_check(ai.system_prompt(stack, topic),
                                      prompt(q, req.get("text", ""), answer, level, refs))
            result = normalise(raw, {r["id"] for r in refs})
        except ImportError:
            note = "The `anthropic` package is not installed; used the offline mock."
        except Exception as e:   # API, network or malformed JSON: degrade, don't lose the attempt
            note = f"AI check failed ({type(e).__name__}: {e}); used the offline mock."
    if result is None:
        provider = "mock"
        result = normalise(mock_check(q, answer, refs), {r["id"] for r in refs})
        note = note or "Offline mock: it can confirm claims the bank supports but cannot detect wrong ones."
    result.update(provider=provider, note=note, refs=[{"id": r["id"], "title": r["title"]} for r in refs],
                  prompt_version=PROMPT_VERSION if provider == "claude" else "mock",
                  model=config.ANTHROPIC_MODEL if provider == "claude" else "offline mock")
    return result
