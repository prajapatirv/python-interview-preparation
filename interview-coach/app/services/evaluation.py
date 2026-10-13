"""Eval harness for the answer checker (Phase E).

``evals/checker_cases.json`` holds answers with *planted* claims whose truth is known. Running the checker
on them gives numbers that must not drop when the prompt or the model changes:

- **error recall**: planted wrong claims the checker flagged ``incorrect``/``outdated``;
- **false-alarm rate**: planted right claims the checker flagged wrong;
- **coverage**: planted claims the checker found at all (matched by a substring of the claim text).

The offline mock cannot flag errors, so a run on it is reported as ``evaluable: false`` and never passes
a gate - evals need the Claude provider.
"""
import json
import time
from pathlib import Path

from .. import config
from . import checker

CASES_FILE = config.BASE_DIR / "evals" / "checker_cases.json"
RUNS_FILE = "eval_runs.jsonl"
WRONG = {"incorrect", "outdated"}
RIGHT = {"correct", "partially_correct"}


def load_cases(path: Path = CASES_FILE) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["cases"]


def score_case(case: dict, check: dict) -> list[dict]:
    """One row per planted claim: whether it was found and whether the verdict was on the right side."""
    rows = []
    for planted in case["planted"]:
        needle = planted["contains"].lower()
        found = next((c for c in check["claims"] if needle in c["text"].lower()), None)
        want_wrong = planted["truth"] == "wrong"
        got_wrong = found is not None and found["verdict"] in WRONG
        rows.append({"case": case["id"], "contains": planted["contains"], "truth": planted["truth"],
                     "found": found is not None, "verdict": found["verdict"] if found else None,
                     "ok": found is not None and (got_wrong == want_wrong)})
    return rows


def summarise(rows: list[dict], provider: str, prompt_version: str, model: str) -> dict:
    wrong = [r for r in rows if r["truth"] == "wrong"]
    right = [r for r in rows if r["truth"] == "right"]
    rate = lambda n, d: round(n / d, 3) if d else None            # noqa: E731
    return {
        "provider": provider, "evaluable": provider == "claude", "prompt_version": prompt_version, "model": model,
        "claims": len(rows), "coverage": rate(sum(r["found"] for r in rows), len(rows)),
        "error_recall": rate(sum(r["ok"] for r in wrong), len(wrong)),
        "false_alarm_rate": rate(sum(r["found"] and not r["ok"] for r in right), len(right)),
        "failures": [r for r in rows if not r["ok"]],
    }


def passes(summary: dict, min_recall: float = 0.75, max_false_alarm: float = 0.2) -> bool:
    return bool(summary["evaluable"] and summary["error_recall"] is not None
                and summary["error_recall"] >= min_recall
                and (summary["false_alarm_rate"] or 0) <= max_false_alarm)


async def run(lib, stack: str, cases: list[dict]) -> dict:
    by_title = {q["title"]: q for q in lib.questions(stack)}
    rows, skipped, provider, version, model = [], [], "mock", "mock", "offline mock"
    for case in cases:
        q = by_title.get(case["question_title"])
        if q is None:
            skipped.append(case["id"])
            continue
        check = await checker.check_answer(lib, {"stack": stack, "question_id": q["id"], "answer": case["answer"]})
        provider, version, model = check["provider"], check["prompt_version"], check["model"]
        rows += score_case(case, check)
    out = summarise(rows, provider, version, model)
    out.update(skipped_cases=skipped, ran_at=time.time())
    return out


def record(summary: dict) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (config.DATA_DIR / RUNS_FILE).open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary) + "\n")


def history(limit: int = 20) -> list[dict]:
    path = config.DATA_DIR / RUNS_FILE
    if not path.is_file():
        return []
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines[-limit:]]
