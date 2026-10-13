# Interview Coach

Scenario-based interview preparation for **Java** and **Python**, from freshers to architects, with an
AI coach (Claude API) and a fully usable offline mode.

It reads **every** question already in this workspace — crib sheets, deep dives, the Q&A guides, the
Python question index — plus the new **scenario answer banks**, organises them by topic, and adds
practice, mock interviews and job-description planning on top.

```bash
./start.sh          # Windows: start.cmd   -> http://127.0.0.1:8100   (stop: ./stop.sh / stop.cmd)
```

First run creates `.venv`, installs `requirements-dev.txt` and copies `.env.example` to `.env`.
Put `ANTHROPIC_API_KEY=...` in `.env` for the real coach; without it the app runs in **offline mock
mode** (answers and scorecards built from the bank itself).

## What a learner can do

| Screen | What it does | Needs a key? |
|---|---|---|
| **Topics** | Every topic for the stack, question counts by source, progress. Inside a topic: filter by experience band (fresher 0–2 · mid 3–6 · senior 6–10 · architect 10+), by source, search; reading list of deep dives; runnable example files. | No |
| **Question card** | Scenario answers render as *live scenario → what they're checking → how I answer → trade-offs → monitoring → follow-ups → 60-second answer*. "I can answer this" tracks progress. | No |
| **Practice mode** | Hides the answer; you type yours first, then get a scorecard, a rewrite, or reveal the model answer. | Better with |
| **Quick revision** | Shows only the 60-second answers. | No |
| **Go deeper** | A second scenario, edge cases and the three hardest follow-ups for that question. | Yes |
| **Ask anything** | Free question ("How can we do rebalancing in Kafka?") answered scenario-first, grounded on the closest bank questions (listed under the answer). | Better with |
| **Mock interview** | Pick topics + level + count; questions come from the bank (scenarios first); each answer is scored on five dimensions; the round ends with averages and your weakest dimension. Scores are kept per topic. | Better with |
| **Job description** | Paste a JD; get matched topics, a study plan, likely questions and stories to prepare. | Better with |
| **Draft a new question** | The AI writes a new scenario question in the bank format; **Save** appends it to the topic's scenario bank (tagged `ai-draft`). | Yes |
| **Check my answer** | In Practice mode: your answer is split into claims, each judged correct / partly correct / incorrect / outdated / could not verify against the bank, with the correction, what was missing, a scorecard and a stronger answer. Every check is stored. | Real verdicts need a key; the mock only confirms what the bank supports |
| **My answers / alternatives** | Save a checked answer under a label (e.g. "Spring Kafka angle"); submit it as *another strong answer*. An automatic gate (no wrong/outdated claim, depth and trade-offs >= 4, >= 40 words) decides whether a reviewer sees it. | Key for a meaningful gate |
| **Review** | Reviewer queue; approving writes `**Another strong answer (<angle>)**` into the question's own Markdown file. | No |
| **Progress** | Average score and wrong-claim rate per topic, weakest questions, repeated mistakes, and the checker eval history. | No |
| **Coverage** | Every question-bearing Markdown file in the repos, its kind, topic and count — and anything not wired in. | No |

Deep link to one question: `#/<stack>/q/<id>`.

## How content is organised (no code changes to add content)

```text
interview-coach/skills/<stack>/_persona.md   stack: content root, guides, index; body = AI persona
interview-coach/skills/<stack>/NN_topic.md   one topic ("skill"): crib, docs, examples, folders, keywords;
                                             body = the AI instruction pack for that topic
<content root>/interview-scenarios/*.md      scenario banks; front matter `skill:` attaches them to a topic
```

Question sources and how each reaches a topic:

| Kind | Source | Topic assignment |
|---|---|---|
| `scenario` | `*/interview-scenarios/*.md` | `skill:` in the bank's front matter |
| `crib` | `java-interview-prep/topics/*.md` | listed in the skill file |
| `deepdive` | `*/deep_dive/*.md` ("Interview questions and full answers") | listed in the skill file |
| `guide` | the Java Q&A guides (mixed topics) | keyword classification (`keywords:`), fallback `general` |
| `index` | `python-interview-prep/QUESTION_INDEX.md` | folder number (`folders:`), else keywords |

`java-interview-prep/QUESTION_INDEX.md` is not read: it is generated from `topics/` by `build_site.py`.

### Scenario answer format (machine-read)

```markdown
### Q12 [senior] How do you handle consumer-group rebalancing in production?
tags: rebalancing, static-membership, kip-848

**The live scenario**
**What the interviewer is really checking**
**How I answer it**
**Trade-offs and what can go wrong**
**How I'd monitor it**
**Numbers I quote**            (optional)
**Follow-ups to expect**       - *question* -> answer
**60-second answer**
**Minimal config**             (optional, at most ~5 lines)
```

Levels: `fresher`, `mid`, `senior`, `architect` (crib levels basic/intermediate/advanced/design map onto them).

## Architecture

```text
app/main.py -> app/api/routes.py -> app/services/{library, bank, retrieve, ai, checker, submissions,
                                                  insights, evaluation, auth, store, supabase_store}.py -> app/config.py
```

- `services/bank.py` — parsers for every question format (headings, sections, index bullets).
- `services/library.py` — loads stacks/topics/questions from the skill files; `coverage()`; saving.
  Held in a `LibraryHolder` on `app.state` so `/api/reload` swaps it atomically.
- `services/retrieve.py` — keyword/IDF retrieval for grounding (no vector DB at this size).
- `services/ai.py` — prompt building + two providers behind `stream_answer()`: Claude (streaming,
  system prompt cached per topic, `effort` from config, server-side refusal fallback) and the offline mock.
- `services/checker.py` — answer fact-check (JSON from Claude, normalised; offline mock fallback), `PROMPT_VERSION`.
- `services/store.py` / `supabase_store.py` — attempts and submissions. SQLite (`data/coach.db`, single user)
  by default; Supabase when `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` are set. Schema: `supabase/schema.sql`;
  copy local data with `scripts/migrate_sqlite_to_supabase.py`.
- `services/auth.py` — Supabase bearer token verified against `/auth/v1/user`; reviewer = `app_metadata.role`
  or `COACH_REVIEWERS`. Without Supabase the single local user is also the reviewer.
- `services/evaluation.py` + `evals/checker_cases.json` + `scripts/run_eval.py` — planted-error eval of the
  checker (error recall, false-alarm rate); needs the Claude provider, the mock is reported as not evaluable.
- `static/index.html` — single page, no CDN, light/dark, hash routing.

Settings (env or `.env`): `ANTHROPIC_API_KEY`, `AI_MODE` (`auto`|`claude`|`mock`), `ANTHROPIC_MODEL`
(default `claude-sonnet-5-5`), `AI_EFFORT` (`medium`), `AI_MAX_TOKENS`, `AI_FALLBACKS` (1),
`PORT` (8100), `COACH_ALLOW_SAVE` (1), `COACH_ROOT` (workspace root), `COACH_SKILLS`, `COACH_DATA`,
`SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_KEY`, `COACH_REVIEWERS`, `GATE_MIN_DEPTH`,
`GATE_MIN_TRADEOFFS`, `GATE_MIN_WORDS`.

## Tests

```bash
.venv/Scripts/python.exe -m pytest      # 61 tests; Linux/macOS: .venv/bin/python -m pytest
```

`tests/test_real_repo.py` runs against the real content and is the **"nothing forgotten" canary**:
it fails if any question file is not wired into a topic, if the crib count drops below 473, if a
scenario answer misses a required section, or if the `general` bucket grows (a keyword gap).
