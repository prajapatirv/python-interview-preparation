"""Links runnable examples to the long-form `deep_dive/*.md` documents.

The mapping is read from the `deep_dive/README.md` tables, e.g.
`| [03](03_decorators.md) | **Decorators** | [`03_decorators.py`](../01_python_core/03_decorators.py) |`,
so it stays correct when the repo's own index changes. A link to a whole folder
(`../02_concurrency/`) is stored under the key `'02_concurrency/'` and applies to every
example in that folder.
"""
import re
from pathlib import Path

ROW_RE = re.compile(r"^\|\s*\[(\d+)\]\(([\w.\-]+\.md)\)\s*\|(.*)$")
TARGET_RE = re.compile(r"\]\(\.\./([\w\-]+)/([\w.\-]*)\)")
TITLE_RE = re.compile(r"\*\*(.+?)\*\*")


def build_map(root: Path) -> dict[str, list[dict]]:
    """Returns {'<topic>/<file>.py' | '<topic>/': [{id, title}]}."""
    readme = root / "deep_dive" / "README.md"
    if not readme.is_file():
        return {}
    out: dict[str, list[dict]] = {}
    for line in readme.read_text(encoding="utf-8", errors="ignore").splitlines():
        row = ROW_RE.match(line)
        if not row:
            continue
        doc_id = row.group(2)[:-3]
        title = TITLE_RE.search(row.group(3))
        entry = {"id": doc_id, "title": f"{row.group(1)} - {title.group(1) if title else doc_id}"}
        for topic, name in TARGET_RE.findall(row.group(3)):
            bucket = out.setdefault(f"{topic}/{name}", [])
            if entry not in bucket:
                bucket.append(entry)
    return out


def docs_for(mapping: dict[str, list[dict]], topic: str, file: str) -> list[dict]:
    """Docs linked to the exact file, then docs linked to its whole folder (deduplicated)."""
    merged: list[dict] = []
    for entry in mapping.get(f"{topic}/{file}", []) + mapping.get(f"{topic}/", []):
        if entry not in merged:
            merged.append(entry)
    return merged


def read_doc(root: Path, doc_id: str) -> str | None:
    """Only files that are really inside deep_dive/ are served (no path traversal)."""
    base = (root / "deep_dive").resolve()
    path = (base / f"{doc_id}.md").resolve()
    if path.parent != base or not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="ignore")
