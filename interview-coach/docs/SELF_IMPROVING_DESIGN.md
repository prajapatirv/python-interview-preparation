# Design — a self-improving Interview Coach

Status: **PROPOSAL, nothing built yet.** Decisions needed are in section 9.

## 1. What we want

1. **Check my answer.** A learner writes their own answer to any question and the coach checks it: which
   statements are correct, which are wrong or outdated, what is missing, plus a scorecard.
2. **Many good answers per question.** One question can have several strong answers (a Spring Kafka angle
   and a plain-client angle; a start-up story and an enterprise story). Learners can save theirs, and the
   good ones can join the bank.
3. **The coach improves itself over time.** Every attempt, score, correction and unanswered question is a
   signal. The system turns those signals into better content, without a human having to notice first.
4. **Ready for many users** (fresher to architect), since the goal is a public launch.

## 2. The core principle: separate *evidence* from *truth*

| Layer | Holds | Store | Who writes |
|---|---|---|---|
| **Curated content** (truth) | Questions, model answers, approved alternative answers | Markdown in git (as today) | Humans, or AI drafts **after review** |
| **Interaction data** (evidence) | Users, attempts, fact-check results, saved answers, votes, reports, unmatched questions | **Supabase** (Postgres) | The app, automatically |
| **AI workflows** | Live checking; offline curation | Claude API; LangGraph for curation | The app |

Why not let the AI write straight into the Markdown files? An AI that edits its own source of truth
without review slowly drifts. Errors compound, and you can no longer say which content was verified.
Keeping truth in git means every change is a reviewable diff, the existing tests still guard it, and the
app works offline. The database can grow freely because nothing in it is "the answer" until it is promoted.

## 3. Architecture

```text
                        ┌──────────────────────────── Browser (static/index.html) ───────────────────────────┐
                        │  Topics · Practice · CHECK MY ANSWER · My answers · Alternative answers · Review     │
                        └───────────────┬───────────────────────────────────────────────────┬──────────────┘
                                        │ HTTPS (+ Supabase Auth JWT)                        │
                     ┌──────────────────▼───────────────────┐                ┌───────────────▼──────────────┐
                     │ FastAPI  (interview-coach/app)        │                │ Supabase                     │
                     │  api/  ->  services/                  │  supabase-py   │  Auth (users, roles)         │
                     │   library   (Markdown bank, as today) │◄──────────────►│  Postgres + Row Level Sec.   │
                     │   checker   (fact-check, live)        │                │  pgvector (semantic search)  │
                     │   store     (repository interface)    │                │  Storage (exports, dumps)    │
                     │   ai        (Claude API, as today)    │                └───────────────▲──────────────┘
                     └──────────────────┬───────────────────┘                                │
                                        │ reads signals / writes drafts                       │
                     ┌──────────────────▼──────────────────────────────────────────────────────┴───────┐
                     │ Curator (LangGraph, runs nightly or on demand, outside the request path)          │
                     │  collect signals -> cluster -> draft improvements -> fact-check drafts -> eval     │
                     │  -> HUMAN REVIEW (interrupt) -> open GitHub PR to the Markdown bank               │
                     └───────────────────────────────────────────────────────────────────────────────────┘
```

## 4. Feature: "Check my answer" (live, per request)

**Flow** — one Claude call with structured output, grounded on the bank:

1. Input: the question, the learner's answer, their level, and the reference material — the question's
   model answer, approved alternative answers, and the 2–3 closest bank entries.
2. Claude returns **JSON matching a schema** (structured outputs), not free text:

```json
{
  "claims": [
    {"text": "auto-commit commits what was processed", "verdict": "incorrect",
     "correction": "it commits what poll() returned, on a timer", "source": "<question id>"},
    {"text": "static membership avoids rebalances on restart", "verdict": "correct", "source": "..."},
    {"text": "KIP-848 is GA in Kafka 3.5", "verdict": "outdated",
     "correction": "generally available in Kafka 4.0", "source": "web"}
  ],
  "missing": ["monitoring: lag per partition", "trade-off of static membership: slower failover"],
  "scores": {"scenario": 3, "depth": 4, "tradeoffs": 2, "monitoring": 1, "clarity": 4},
  "improved_answer": "...",
  "follow_up": "Why not just raise max.poll.interval.ms?"
}
```

3. The UI highlights each sentence of the learner's answer as green, red or amber, with the correction
   beside it. Then it shows what was missing, the scorecard and the improved answer.
4. **Verdicts:** `correct` · `partially_correct` · `incorrect` · `outdated` · `unverifiable`. The checker
   must say *unverifiable* rather than guess, and every verdict cites a source: a bank question id, or
   `web` when the optional web-search tool was used for version-sensitive facts.
5. Stored in Supabase as an `attempt` (section 6), which feeds both the learner's progress and the curator.

**Why not LangGraph here:** this is a single, latency-sensitive call. A graph framework adds hops and
abstraction without adding capability. Use the Anthropic SDK directly, as the coach already does
(streaming, prompt caching, a refusal fallback).

## 5. Feature: many answers per question

| Kind | Visibility | Lives in |
|---|---|---|
| **Model answer** | everyone | Markdown (today's answer) |
| **Approved alternative** ("another strong answer — *Spring Kafka angle*") | everyone | Markdown, in a new optional section `**Another strong answer (<angle>)**` |
| **My answer** (saved attempt, with its latest check) | the learner only | Supabase |
| **Submitted alternative** (a learner proposes theirs) | reviewers | Supabase → promoted to Markdown by PR |

Promotion rule: a submitted alternative is **auto fact-checked**. Only submissions with no
`incorrect`/`outdated` claims and a score of at least 4 on depth and trade-offs reach the review queue.
A reviewer approves, and the curator opens a PR adding it to the Markdown file. The parser needs one small
change to show the new section; existing files are unaffected.

## 6. Data model (Supabase / Postgres)

```text
profiles        id (= auth.users.id), display_name, target_level, stacks[], created_at
attempts        id, user_id, question_id, stack, topic, level, answer_text, check_json, scores jsonb,
                total_score, model, prompt_version, created_at
saved_answers   id, user_id, question_id, attempt_id, label, is_submitted, created_at
submissions     id, saved_answer_id, status (pending|approved|rejected|promoted), reviewer_id,
                review_note, pr_url, updated_at
feedback        id, user_id, question_id, kind (helpful|wrong|outdated|unclear), comment, created_at
gaps            id, user_id, stack, query_text, best_match_id, best_match_score, created_at
                -- "Ask anything" questions the bank could not answer well
drafts          id, kind (new_question|fix_answer|alternative|common_mistakes), stack, topic,
                target_question_id, markdown, evidence jsonb, eval_result jsonb,
                status (draft|in_review|approved|rejected|merged), pr_url, created_at
question_stats  question_id, attempts, avg_score, wrong_claim_rate, top_misconceptions jsonb  (materialised view)
embeddings      question_id, content_hash, embedding vector(…)   -- pgvector, replaces keyword retrieval
```

- **Row Level Security:** learners see only their own attempts and saved answers; reviewers (a role)
  see submissions and drafts; nobody can write to `drafts` except the curator's service key.
- **Question ids** are the existing stable hashes, so Markdown and database stay linked.
- **Privacy:** answers are personal data. Use per-user deletion and export, and never send emails or names to the model.

## 7. The self-improvement loop (Curator, LangGraph)

LangGraph fits here: a multi-step workflow with branches, retries, durable state, and a **human-in-the-loop
pause**. Its Postgres checkpointer can live in the same Supabase database.

```text
collect_signals -> cluster -> draft -> verify -> evaluate -> human_review (interrupt) -> publish_pr
```

1. **collect_signals:** from the last N days —
   - questions with a low average score or a high wrong-claim rate;
   - the most common incorrect claims (misconceptions);
   - `feedback` marked wrong or outdated;
   - `gaps` (Ask-anything questions with no good match);
   - topics with few scenario questions.
2. **cluster:** group similar gaps and misconceptions (embeddings), so one draft fixes many reports.
3. **draft** (Claude, in the bank format), one of:
   - a **new scenario question** for a gap cluster;
   - a **fix** to an answer reported wrong or outdated;
   - a **"Common mistakes"** section listing the top misconceptions for a question;
   - an **alternative answer** from approved submissions.
4. **verify:** run the fact-checker on the draft itself, with web search for version facts. Any
   `incorrect`/`outdated` claim sends it back to `draft` (at most 2 loops), then drops it.
5. **evaluate:** the format parser must accept it, the coverage and real-repo tests must pass, and it must
   not duplicate an existing question (embedding similarity).
6. **human_review:** the graph pauses; the draft appears on a **Review** screen in the app with its
   evidence ("38 learners claimed X; the bank never addressed it"). Approve, edit or reject.
7. **publish_pr:** approved drafts become a branch and a GitHub pull request on the content repo. Merging
   it updates the bank; the app reloads it. **Nothing reaches learners without a merged PR.**

**Measuring that it is actually improving** (a dashboard, plus an eval set that runs on every prompt change):

| Signal | Improving means |
|---|---|
| Fact-checker accuracy on a fixed eval set (questions + answers with known errors) | does not drop when prompts or models change |
| Average learner score per topic over time | rises |
| Wrong-claim rate on questions that gained a "Common mistakes" section | falls |
| Gap queries without a good match | fall |
| Draft acceptance rate in review | rises (the curator learns what you approve) |

## 8. Build phases

| Phase | Delivers | Needs |
|---|---|---|
| **A** | "Check my answer" with structured fact-check, claim highlighting, saved answers. A `store` interface with a **local SQLite** implementation, so it works for you immediately | API key |
| **B** | Supabase: Auth, RLS, the tables above, migration from SQLite, pgvector retrieval | Supabase project |
| **C** | Alternative answers: submit, auto-check, review queue, Markdown section | B |
| **D** | Curator in LangGraph: signals, drafts, verification, Review screen, GitHub PR | B, GitHub token |
| **E** | Eval set and improvement dashboard; prompt and model changes gated by the eval | A |

## 9. Decisions needed

1. **Storage start:** SQLite first and Supabase in Phase B (*recommended*: value now, no account needed yet),
   or Supabase from day one?
2. **LangGraph scope:** only for the curator loop (*recommended*), or for every AI feature?
3. **Web search in fact-checking** for version-sensitive facts (Kafka/Java/Spring releases): improves
   freshness, adds cost and latency per check. On for curator drafts only (*recommended*), or for every check?
4. **Who approves content:** only you at first (*recommended*), or a reviewer role for trusted users later?
5. **Public launch timing:** with sign-up and RLS from Phase B, or single-user until later?

**Prerequisite for any AI phase:** a valid Anthropic API key (`sk-ant-api…`) in `interview-coach/.env`.
