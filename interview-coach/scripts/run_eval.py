"""Run the checker eval set and gate on it. Exit code 1 means the checker got worse (or cannot be evaluated).

    .venv/Scripts/python.exe scripts/run_eval.py                       # needs a real API key
    .venv/Scripts/python.exe scripts/run_eval.py --min-recall 0.8 --max-false-alarm 0.1 --no-record

Run it after every change to the checker prompt (``checker.CHECK_FORMAT``) or ``ANTHROPIC_MODEL``.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import evaluation, library  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stack", default="java")
    ap.add_argument("--min-recall", type=float, default=0.75)
    ap.add_argument("--max-false-alarm", type=float, default=0.2)
    ap.add_argument("--no-record", action="store_true", help="do not append the run to data/eval_runs.jsonl")
    args = ap.parse_args()
    lib = library.Library.load()
    summary = asyncio.run(evaluation.run(lib, args.stack, evaluation.load_cases()))
    ok = evaluation.passes(summary, args.min_recall, args.max_false_alarm)
    summary["passed"] = ok
    if not args.no_record:
        evaluation.record(summary)
    print(json.dumps(summary, indent=2))
    if not summary["evaluable"]:
        print("\nNot evaluable: the offline mock cannot flag wrong claims. Set ANTHROPIC_API_KEY.", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
