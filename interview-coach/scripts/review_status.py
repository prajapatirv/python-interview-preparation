"""Which answers have been read by a person, and which have changed since.

The canary tests prove every question is wired in; they cannot tell whether an answer is any good.
The Answer Map's ``scripts/answer_map/reviewed/batchN.json`` files are the record of answers someone
has read. This report joins them with git history, per bank file:

- ``reviewed``: how many of the file's questions are in a reviewed batch;
- ``changed``: how many of those reviewed answers differ from the text at the commit of the batch
  that reviewed them (newest batch wins), so they need reading again;
- ``dirty``: the file has uncommitted edits.

    .venv/Scripts/python.exe scripts/review_status.py              # files with reviewed answers or flags
    .venv/Scripts/python.exe scripts/review_status.py --all        # every bank file
    .venv/Scripts/python.exe scripts/review_status.py --changed    # list the changed answers by title
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import bank, library  # noqa: E402

REVIEWED = Path(__file__).resolve().parent / "answer_map" / "reviewed"


def _git(top: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(top), *args], capture_output=True, text=True, encoding="utf-8",
                          check=check)


def bodies_at(top: Path, commit: str, path: str, stack: str, rel: str, is_index: bool) -> dict[str, str]:
    """Question id -> answer body, for ``path`` as it was at ``commit`` (ids computed as the library does)."""
    shown = _git(top, "show", f"{commit}:{path}", check=False)
    if shown.returncode:
        return {}
    if is_index:
        return {bank.stable_id(stack, rel, q["label"], q["title"]): q["body"] for q in bank.parse_index(shown.stdout)}
    return {q.get("qid") or bank.stable_id(stack, rel, q["label"], q["title"]): q["body"]
            for q in bank.parse_questions(shown.stdout)[2]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all", action="store_true", help="list every bank file, not only reviewed or flagged ones")
    ap.add_argument("--changed", action="store_true", help="also print the title of each changed answer")
    args = ap.parse_args()

    lib = library.Library.load()
    top = Path(_git(lib.root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    prefix = lib.root.resolve().relative_to(top).as_posix()
    prefix = "" if prefix == "." else prefix + "/"
    dirty = {line[3:].strip().strip('"') for line in _git(top, "status", "--porcelain").stdout.splitlines()}

    # question id -> commit of the newest batch that lists it (uncommitted batches count as the working tree)
    reviewed_in: dict[str, str] = {}
    for b in sorted(REVIEWED.glob("batch*.json"), key=lambda p: int("".join(c for c in p.stem if c.isdigit()))):
        rel_batch = b.resolve().relative_to(top).as_posix()
        commit = _git(top, "log", "-1", "--format=%H", "--", rel_batch).stdout.strip()
        for qid in json.loads(b.read_text(encoding="utf-8")):
            reviewed_in[qid] = "" if rel_batch in dirty or not commit else commit

    total_changed = 0
    for s in lib.stacks:
        by_file: dict[str, list[dict]] = {}
        for q in lib.questions(s.id):
            by_file.setdefault(q["source"], []).append(q)
        done = sum(1 for q in lib.questions(s.id) if q["id"] in reviewed_in)
        print(f"\n{s.id}: {done} of {len(lib.questions(s.id))} answers reviewed")
        print(f"  {'reviewed':>9}  changed  dirty  file")
        for path in sorted(by_file):
            qs = by_file[path]
            seen = [q for q in qs if q["id"] in reviewed_in]
            snapshots: dict[str, dict[str, str]] = {}
            changed = []
            for q in seen:
                commit = reviewed_in[q["id"]]
                if not commit:
                    continue                       # reviewed in a batch not committed yet: nothing to compare
                if commit not in snapshots:
                    snapshots[commit] = bodies_at(top, commit, prefix + path, s.id, path, q["kind"] == "index")
                if snapshots[commit].get(q["id"]) != q["body"]:
                    changed.append(q)
            is_dirty = prefix + path in dirty
            if not (args.all or seen or is_dirty):
                continue
            total_changed += len(changed)
            print(f"  {len(seen):>4}/{len(qs):<4}  {len(changed) or '':>7}  {'yes' if is_dirty else '':5}  {path}")
            if args.changed:
                for q in changed:
                    print(f"{'':25}- {q['id']}  {q['title'][:80]}")
    print(f"\n{total_changed} reviewed answer(s) changed since they were reviewed")
    return 1 if total_changed else 0


if __name__ == "__main__":
    sys.exit(main())
