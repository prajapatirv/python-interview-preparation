"""Runs every stdlib-only Python example and fails if any exits non-zero.

Replaces the shell loop in CLAUDE.md. Two things make it catch what the loop catches, on any OS:

- stdout is a pipe, never a terminal, so the example cannot rely on a console encoding;
- PYTHONIOENCODING=cp1252 forces the encoding Windows uses for redirected output, so a stray
  arrow or Greek letter in a print() fails here on Linux CI too, not only on a Windows machine.

    py scripts/verify_examples.py               # all of them
    py scripts/verify_examples.py 06_kafka      # only paths containing this text
"""
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PREP = Path(__file__).resolve().parent.parent / "python" / "python-interview-prep"

# The examples that need nothing beyond the standard library. 03 (pandas), 04/05 (pytest, FastAPI) and
# 06_kafka/01-02 (a live broker) are covered by the test suites instead.
PATTERNS = [
    "01_python_core/*.py", "02_concurrency/*.py", "06_kafka/0[3-8]*.py", "07_caching_queues/*.py",
    "08_scaling_production_resilience/*.py", "09_aws_lambda_streaming/*.py", "10_genai_llm_patterns/*.py",
    "11_coding_challenges/*.py", "12_framework_internals/*.py", "13_system_design_scenarios/*.py",
    "14_airflow_orchestration/0*.py",
]
EXPECTED = 59           # a drop means a glob above stopped matching files; raise it when examples are added
TIMEOUT_S = 180


def run(path: Path) -> tuple[Path, int, float, str]:
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONDONTWRITEBYTECODE": "1"}
    start = time.perf_counter()
    try:
        p = subprocess.run([sys.executable, path.name], cwd=path.parent, env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, encoding="cp1252", errors="replace", timeout=TIMEOUT_S)
        code, err = p.returncode, p.stderr
    except subprocess.TimeoutExpired:
        code, err = -1, f"timed out after {TIMEOUT_S}s"
    return path, code, time.perf_counter() - start, err


def main(argv: list[str]) -> int:
    files = sorted({f for pat in PATTERNS for f in PREP.glob(pat)})
    if argv:
        files = [f for f in files if any(a in f.as_posix() for a in argv)]
    elif len(files) != EXPECTED:
        print(f"expected {EXPECTED} examples, found {len(files)}: update PATTERNS or EXPECTED")
        return 1
    failed = 0
    with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as pool:
        for path, code, secs, err in pool.map(run, files):
            rel = path.relative_to(PREP).as_posix()
            print(f"{'ok  ' if code == 0 else 'FAIL'} {secs:5.1f}s  {rel}")
            if code != 0:
                failed += 1
                print("      " + "\n      ".join(err.strip().splitlines()[-6:]))
    print(f"\n{len(files) - failed}/{len(files)} examples passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
