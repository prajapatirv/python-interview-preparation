"""Which answers have been read by a person, and which have changed since.

The canary tests prove every question is wired in; they cannot tell whether an answer is any good.
The Answer Map's ``scripts/answer_map/reviewed/batchN.json`` files are the record of answers someone
has read. This report joins them with git history, per bank file:

- ``reviewed``: how many of the file's questions are in a reviewed batch;
- ``STALE``: the file was committed after the newest batch that reviewed one of its questions,
  so at least one reviewed answer may have changed since it was read (re-read the diff);
- ``dirty``: the file has uncommitted edits.

    .venv/Scripts/python.exe scripts/review_status.py              # files with reviewed answers or flags
    .venv/Scripts/python.exe scripts/review_status.py --all        # every bank file
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import library  # noqa: E402

REVIEWED = Path(__file__).resolve().parent / "answer_map" / "reviewed"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout


def last_commit_times(root: Path, paths: set[str]) -> dict[str, int]:
    """Newest commit time per path, from one ``git log`` walk."""
    out, when = {}, 0
    for line in _git(root, "log", "--format=@%ct", "--name-only", "--", *sorted(paths)).splitlines():
        if line.startswith("@"):
            when = int(line[1:])
        elif line and line not in out:
            out[line] = when
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all", action="store_true", help="list every bank file, not only reviewed or flagged ones")
    args = ap.parse_args()

    lib = library.Library.load()
    root = lib.root
    top = Path(_git(root, "rev-parse", "--show-toplevel").strip())
    prefix = root.resolve().relative_to(top.resolve()).as_posix()
    prefix = "" if prefix == "." else prefix + "/"

    batches = sorted(REVIEWED.glob("batch*.json"))
    batch_paths = {b.resolve().relative_to(top.resolve()).as_posix() for b in batches}
    sources = {src["path"] for s in lib.stacks for src in s.sources}
    times = last_commit_times(top, {prefix + p for p in sources} | batch_paths)
    dirty = {line[3:].strip().strip('"') for line in _git(top, "status", "--porcelain").splitlines()}

    reviewed_at: dict[str, int] = {}                    # question id -> commit time of the batch that holds it
    for b in batches:
        t = times.get(b.resolve().relative_to(top.resolve()).as_posix(), 0)
        for qid in json.loads(b.read_text(encoding="utf-8")):
            reviewed_at[qid] = max(reviewed_at.get(qid, 0), t)

    stale_files = 0
    for s in lib.stacks:
        by_file: dict[str, list[dict]] = {}
        for q in lib.questions(s.id):
            by_file.setdefault(q["source"], []).append(q)
        done = sum(1 for q in lib.questions(s.id) if q["id"] in reviewed_at)
        print(f"\n{s.id}: {done} of {len(lib.questions(s.id))} answers reviewed")
        print(f"  {'reviewed':>9}  {'changed':10}  flags  file")
        for path in sorted(by_file):
            qs = by_file[path]
            seen = [reviewed_at[q["id"]] for q in qs if q["id"] in reviewed_at]
            changed = times.get(prefix + path, 0)
            flags = []
            if seen and changed > max(seen):
                flags.append("STALE")
                stale_files += 1
            if prefix + path in dirty:
                flags.append("dirty")
            if not (args.all or seen or flags):
                continue
            day = datetime.fromtimestamp(changed).strftime("%Y-%m-%d") if changed else "uncommitted"
            print(f"  {len(seen):>4}/{len(qs):<4}  {day:10}  {' '.join(flags):5}  {path}")
    print(f"\n{stale_files} file(s) changed after their answers were reviewed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
