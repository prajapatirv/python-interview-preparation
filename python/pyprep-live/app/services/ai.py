"""AI coach with two interchangeable providers behind `stream_answer()`.

- **claude**: streams from the Anthropic API (needs ANTHROPIC_API_KEY).
- **mock**:   offline, deterministic answers built from the example's own source and captured
              log (docstring, outline, EXPERIMENT comments, exit status, errors). No network.

AI_MODE=auto (default) uses claude when a key is present, otherwise mock; `claude` or `mock`
force one. To add another provider (e.g. Bedrock `converse_stream`), add an async generator
with the same signature and select it in `mode()`.
"""
import asyncio
import os
import re

from .. import config
from .catalog import analyse_source

SYSTEM = (
    "You are a senior Python interview coach. The learner is an experienced Java/Spring "
    "engineer (12+ years) preparing for senior Python backend interviews. Be concrete, "
    "reference the exact lines/outputs shown, contrast with Java where semantics differ, "
    "and keep answers under 350 words unless asked for more."
)

MODES = {
    "explain": "Explain what this program demonstrates and walk through the log output line by line, "
               "calling out the one or two lines that an interviewer would care about most.",
    "quiz": "Write 5 interview questions (mixed difficulty) based on this example and its output. "
            "Give a short model answer for each, hidden under an 'Answer:' line.",
    "break": "Suggest 3 small modifications ('EXPERIMENTS') the learner should make to this code, "
             "and predict precisely what output changes for each.",
    "java": "Contrast this with the equivalent Java/Spring approach. Where do semantics differ and why?",
    "predict": "Do NOT reveal the output. Ask the learner to predict what this program prints, "
               "give 3 specific things to predict, and wait for their answer.",
    "ask": "Answer the learner's question about this example.",
}


def mode() -> str:
    """The provider actually in use: 'claude' or 'mock'."""
    wanted = os.getenv("AI_MODE", "auto").lower()
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    if wanted == "mock" or (wanted in ("auto", "claude") and not has_key):
        return "mock"
    return "claude"


def available() -> bool:
    """True when answers come from the real model (the UI shows 'mock' otherwise)."""
    return mode() == "claude"


def build_prompt(mode_: str, source: str, output: str, question: str = "") -> str:
    prompt = (f"{MODES.get(mode_, MODES['explain'])}\n\n<source>\n{source[:12000]}\n</source>\n\n"
              f"<log_output>\n{output[-6000:]}\n</log_output>")
    if question:
        prompt += f"\n\n<question>{question}</question>"
    return prompt


# ---------------------------------------------------------------- mock provider

def mock_answer(mode_: str, source: str, output: str, question: str = "") -> str:
    a = analyse_source(source)
    sections, exps = a["sections"], a["experiments"]
    doc = next((ln.strip() for ln in a["doc"].splitlines() if ln.strip()), "this example")
    out_lines = [ln for ln in output.splitlines() if ln.strip()]
    errors = [ln for ln in out_lines if re.search(r"Traceback|Error\b|FAILED", ln)]
    outline = "\n".join(f"  - line {s['line']}: {s['title']}" for s in sections) or "  (no section markers found)"
    note = "\n\n(mock mode: offline answer built from the source and log. Set ANTHROPIC_API_KEY for the real coach.)"

    if mode_ == "explain":
        log = (f"The log has {len(out_lines)} non-empty lines." if out_lines
               else "Run the example first so the log can be explained.")
        if errors:
            log += f" Lines worth a look: {errors[0][:120]!r}."
        return (f"What it demonstrates: {doc}\n\nStructure:\n{outline}\n\n{log}\n"
                f"Tip: read the outline top to bottom, then match each section to the banner it prints "
                f"in the log. Interviewers care most about WHY the behaviour happens, not that it does.{note}")
    if mode_ == "quiz":
        qs = [f"Q{i}. In '{s['title']}', what is being shown and when would you use it?"
              for i, s in enumerate(sections[:5], 1)] or ["Q1. Summarise what this file demonstrates."]
        qs += [f"Q{len(qs) + 1}. Predict the effect of: {e['text']}" for e in exps[:2]]
        return "Quiz (answer out loud, then check the source and the deep dive):\n\n" + "\n".join(qs) + note
    if mode_ == "break":
        if not exps:
            return "No '# EXPERIMENT:' comments in this file. Try: change a constant, remove a lock/decorator, " \
                   "or swap an input, then predict the new output before re-running." + note
        return "Experiments from the file (edit, predict, run):\n\n" + "\n".join(
            f"  {i}. line {e['line']}: {e['text']}" for i, e in enumerate(exps[:3], 1)) + note
    if mode_ == "java":
        return ("Java contrast checklist for this example:\n"
                "  - Typing: Python is dynamic; Java checks types at compile time.\n"
                "  - Concurrency: the GIL limits CPU-bound threads (Java threads run in parallel).\n"
                "  - Resources: `with` blocks play the role of try-with-resources.\n"
                "  - Decorators/metaprogramming replace many annotation/AOP uses in Spring.\n"
                "See the 'Java contrast' block in the linked deep dive for the exact semantics." + note)
    if mode_ == "predict":
        picks = [s["title"] for s in sections[:3]] or ["the first printed line", "the last printed line"]
        return "Before you run it, write down your prediction for:\n\n" + "\n".join(
            f"  {i}. what '{p}' prints" for i, p in enumerate(picks, 1)) + \
            "\n\nThen press Run and compare with the log." + note
    # ask: show the source lines that match the question's keywords
    words = {w for w in re.findall(r"[A-Za-z_]{4,}", question.lower())}
    hits = [f"  line {i}: {ln.strip()[:100]}" for i, ln in enumerate(source.splitlines(), 1)
            if words and any(w in ln.lower() for w in words)][:8]
    body = "Lines mentioning your keywords:\n" + "\n".join(hits) if hits else \
        "No source line matches those keywords. Try the outline sections:\n" + outline
    return body + note


async def _stream_mock(mode_, source, output, question):
    text = mock_answer(mode_, source, output, question)
    for i in range(0, len(text), 40):               # chunked so the UI streams like the real thing
        yield text[i:i + 40]
        await asyncio.sleep(0.01)


# ---------------------------------------------------------------- claude provider

async def _stream_claude(mode_, source, output, question):
    try:
        from anthropic import AsyncAnthropic        # imported lazily: optional dependency
    except ImportError:
        yield "The `anthropic` package is not installed (pip install anthropic); using mock answer instead.\n\n"
        async for chunk in _stream_mock(mode_, source, output, question):
            yield chunk
        return
    client = AsyncAnthropic()
    try:
        async with client.messages.stream(
                model=config.ANTHROPIC_MODEL, max_tokens=1200, system=SYSTEM,
                messages=[{"role": "user", "content": build_prompt(mode_, source, output, question)}]) as s:
            async for text in s.text_stream:
                yield text
    except Exception as e:                           # surface API problems in the UI, don't 500
        yield f"\n\n[AI error: {type(e).__name__}: {e}]"


async def stream_answer(mode_: str, source: str, output: str, question: str = ""):
    """Yields text chunks from whichever provider `mode()` selects."""
    provider = _stream_claude if mode() == "claude" else _stream_mock
    async for chunk in provider(mode_, source, output, question):
        yield chunk
