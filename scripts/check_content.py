"""Checks the line links in python-interview-prep/QUESTION_INDEX.md.

Each answer ends with a link to the line that demonstrates it, e.g.
`→ [03_decorators.py:42](01_python_core/03_decorators.py#L42)`. Editing an example shifts its lines,
and nothing else notices when a link starts pointing at the wrong place. This fails when:

- the linked file does not exist,
- the label and the anchor disagree (`:42` vs `#L40`), or name a different file,
- the line number is past the end of the file, or the line is blank.

It cannot tell whether a line is still the *right* one; after editing an example, re-read its links.

It also checks ``shared/cross-stack-pairs.md`` (the Java/Python twins both runners link to): every row
must name at least one program on each side, and every link must resolve.

    py scripts/check_content.py
"""
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
PREP = WORKSPACE / "python" / "python-interview-prep"
PAIRS = WORKSPACE / "shared" / "cross-stack-pairs.md"
sys.path.insert(0, str(WORKSPACE / "shared" / "prepkit"))
from prepkit import pairs  # noqa: E402
LINK_RE = re.compile(r"\[([\w.\-]+):(\d+)\]\(([\w./\-]+)#L(\d+)\)")


def check_index(index: Path) -> list[str]:
    problems, cache = [], {}
    for n, line in enumerate(index.read_text(encoding="utf-8").splitlines(), 1):
        for name, label, target, anchor in LINK_RE.findall(line):
            where = f"{index.name}:{n}"
            path = PREP / target
            if not path.is_file():
                problems.append(f"{where}: {target} does not exist")
                continue
            if path.name != name or label != anchor:
                problems.append(f"{where}: label [{name}:{label}] does not match {target}#L{anchor}")
            lines = cache.setdefault(path, path.read_text(encoding="utf-8").splitlines())
            i = int(anchor)
            if not 1 <= i <= len(lines):
                problems.append(f"{where}: {target} has {len(lines)} lines, link points at {i}")
            elif not lines[i - 1].strip():
                problems.append(f"{where}: {target}#L{i} is a blank line")
    return problems


def check_pairs(path: Path) -> tuple[int, list[str]]:
    rows, problems = pairs.load(path), []
    if not rows:
        return 0, [f"{path.name}: no rows parsed"]
    for r in rows:
        if not r["java"] or not r["python"]:
            problems.append(f"{path.name}: row '{r['topic']}' needs a Java and a Python link")
        for target in r["targets"]:
            if not (path.parent / target).exists():
                problems.append(f"{path.name}: row '{r['topic']}' links missing {target}")
    return len(rows), problems


def main() -> int:
    index = PREP / "QUESTION_INDEX.md"
    problems = check_index(index)
    links = sum(len(LINK_RE.findall(ln)) for ln in index.read_text(encoding="utf-8").splitlines())
    n_pairs, pair_problems = check_pairs(PAIRS)
    for p in problems + pair_problems:
        print(p)
    print(f"{links} line links checked, {len(problems)} problem(s)")
    print(f"{n_pairs} Java/Python pairs checked, {len(pair_problems)} problem(s)")
    return 1 if problems or pair_problems else 0


if __name__ == "__main__":
    sys.exit(main())
