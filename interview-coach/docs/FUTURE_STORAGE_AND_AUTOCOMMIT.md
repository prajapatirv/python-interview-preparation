# Future exploration - storage and auto-commit

Status: **parked.** The code for the pieces below exists but is not the current focus. The current focus is
interview questions and answers (content). Come back to this when the content bank is where you want it.

## What exists today (already committed)

| Piece | Where | State |
|---|---|---|
| Attempts and saved answers in SQLite | `app/services/store.py`, `data/coach.db` (gitignored) | works, tested |
| Supabase store, auth, RLS schema | `app/services/supabase_store.py`, `auth.py`, `supabase/schema.sql` | **never run against a live project** |
| SQLite -> Supabase copy | `scripts/migrate_sqlite_to_supabase.py` | tested against a fake only |
| Approved alternative answers written into the Markdown bank | `library.add_alternative()`, `POST /api/review/{id}` | works, tested; edits the file directly |

## Ideas to explore later

1. **Real auto-commit of approved content.** Today approving a submission rewrites a Markdown file and leaves
   it uncommitted. Options: (a) commit to a local branch per approval; (b) open a GitHub PR per batch
   (the Phase D design); (c) keep manual `git commit`. Open questions: who owns the git identity on a hosted
   deployment, how to avoid a merge conflict when two approvals touch one file, and whether the commit should
   run the test canary (`tests/test_real_repo.py`) first and refuse on failure.
2. **Curator (LangGraph).** signals -> cluster -> draft -> verify -> evaluate -> human review -> PR.
   Needs the checker eval to have enough cases to trust its verdicts first.
3. **Supabase go-live.** Create a project, run `schema.sql`, set `COACH_REVIEWERS`, run the migration, test
   sign-in. Decide whether the public launch needs sign-up now or later.
4. **Semantic retrieval (pgvector).** Needs an embedding model; keyword retrieval is fine at the current
   bank size.
5. **Web search in the checker** for version-sensitive facts (Kafka, Java, Spring releases).

## Guardrails to keep

- Evidence (attempts, votes) lives in a database; **truth (the bank) lives in Markdown in git** and changes only
  through a reviewed action.
- Never auto-push content to `main` without the canary tests passing.
- Answers are personal data: per-user deletion and export before any public launch.

Full design: `SELF_IMPROVING_DESIGN.md`.
