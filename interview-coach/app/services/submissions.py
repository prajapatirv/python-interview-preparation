"""Alternative answers: the automatic gate and promotion into the Markdown bank (Phase C).

A saved answer can be *submitted* as another strong answer to its question. The gate is deliberately
mechanical, so a human reviewer only sees submissions worth reading:

- no claim judged ``incorrect`` or ``outdated`` by the checker,
- depth and trade-offs scores of at least ``GATE_MIN_DEPTH`` / ``GATE_MIN_TRADEOFFS`` (4 by default),
- at least ``GATE_MIN_WORDS`` words.

Approval writes the answer into the question's own file as ``**Another strong answer (<angle>)**``.
Nothing reaches other learners without that explicit reviewer action.
"""
from .. import config

BAD_VERDICTS = ("incorrect", "outdated")


def gate(attempt: dict) -> dict:
    check = attempt["check"]
    reasons = []
    bad = [c for c in check.get("claims", []) if c["verdict"] in BAD_VERDICTS]
    if bad:
        reasons.append(f"{len(bad)} claim(s) judged incorrect or outdated, e.g. \"{bad[0]['text'][:80]}\"")
    scores = check.get("scores", {})
    if scores.get("depth", 0) < config.GATE_MIN_DEPTH:
        reasons.append(f"depth score {scores.get('depth', 0)} is below {config.GATE_MIN_DEPTH}")
    if scores.get("tradeoffs", 0) < config.GATE_MIN_TRADEOFFS:
        reasons.append(f"trade-offs score {scores.get('tradeoffs', 0)} is below {config.GATE_MIN_TRADEOFFS}")
    words = len(attempt["answer_text"].split())
    if words < config.GATE_MIN_WORDS:
        reasons.append(f"only {words} words (minimum {config.GATE_MIN_WORDS})")
    return {"passed": not reasons, "reasons": reasons, "provider": attempt["provider"],
            "unverified": attempt["provider"] != "claude"}
