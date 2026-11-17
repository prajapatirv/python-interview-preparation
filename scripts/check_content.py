"""Checks the line links in python-interview-prep/QUESTION_INDEX.md.

Each answer ends with a link to the line that demonstrates it, e.g.
`→ [03_decorators.py:42](01_python_core/03_decorators.py#L42)`. Editing an example shifts its lines,
and nothing else notices when a link starts pointing at the wrong place. This fails when:

- the linked file does not exist,
- the label and the anchor disagree (`:42` vs `#L40`), or name a different file,
- the line number is past the end of the file, or the line is blank.

It cannot tell whether a line is still the *right* one; after editing an example, re-read its links.

    py scripts/check_content.py
"""
import re
import sys
from pathlib import Path

PREP = Path(__file__).resolve().parent.parent / "python" / "python-interview-prep"
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


def main() -> int:
    index = PREP / "QUESTION_INDEX.md"
    problems = check_index(index)
    for p in problems:
        print(p)
    links = sum(len(LINK_RE.findall(ln)) for ln in index.read_text(encoding="utf-8").splitlines())
    print(f"{links} line links checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
