"""Copy local SQLite attempts and submissions into Supabase, assigning them to one Supabase user.

    set SUPABASE_URL=...  &  set SUPABASE_SERVICE_KEY=...
    .venv/Scripts/python.exe scripts/migrate_sqlite_to_supabase.py --user-id <auth.users id> [--dry-run]

Run ``supabase/schema.sql`` first. Rows are re-inserted (ids are reassigned) so run it once; submissions are
re-pointed at their new attempt ids. ``--dry-run`` only counts.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.services.store import SqliteStore  # noqa: E402
from app.services.supabase_store import SupabaseStore  # noqa: E402


def migrate(src, dst, user_id: str) -> tuple[int, int]:
    """Returns (attempts copied, submissions copied). ``dst`` only needs the Store write methods."""
    id_map, n_sub = {}, 0
    for a in src.all_attempts():
        new = dst.add_attempt(question_id=a["question_id"], stack=a["stack"], topic=a["topic"], level=a["level"],
                              answer_text=a["answer_text"], check=a["check"], provider=a["provider"],
                              prompt_version=a.get("prompt_version", ""), user_id=user_id)
        if a["saved"]:
            dst.save(new["id"], a["label"], user_id=user_id)
        id_map[a["id"]] = new
    for s in reversed(src.submissions()):                      # oldest first
        att = id_map.get(s["attempt_id"])
        if att is None:
            continue
        new = dst.add_submission(attempt=att, angle=s["angle"], status=s["status"], gate=s["gate"])
        if s["status"] in ("approved", "promoted") or s["review_note"]:
            dst.review_submission(new["id"], s["status"], note=s["review_note"], reviewer_id=s["reviewer_id"],
                                  promoted_to=s["promoted_to"])
        n_sub += 1
    return len(id_map), n_sub


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--user-id", required=True)
    ap.add_argument("--sqlite", default=str(config.DATA_DIR / "coach.db"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    src = SqliteStore(Path(args.sqlite))
    if args.dry_run:
        print(f"would copy {len(src.all_attempts())} attempts and {len(src.submissions())} submissions")
        return 0
    if not (config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY):
        print("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set", file=sys.stderr)
        return 2
    a, s = migrate(src, SupabaseStore(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY), args.user_id)
    print(f"copied {a} attempts and {s} submissions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
