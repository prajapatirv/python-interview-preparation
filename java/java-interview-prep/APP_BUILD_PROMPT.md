# Task 1 - Reusable Prompts (works for Java, Python, or any stack)

Two prompts. Paste them into Claude Code / Claude in the repo root.

- **Prompt A** builds (or rebuilds) the study app from the topic files.
- **Prompt B** generates a NEW topic file in the exact format the app reads.

The app is data-driven: the app never changes, only `topics/*.md` files change. Python and Java can live in the same repo (`topics/py-*.md`, `topics/java-*.md`) or in two copies of the repo.

---

## Prompt A - Build the interview study app

```
You are a senior engineer building a self-contained interview-prep web app.

GOAL
Create an app that renders technical interview questions and answers from
Markdown files so anyone can reuse it for any language or stack.

INPUT FORMAT (do not change it)
- Folder `topics/` with files named `<nn>-<slug>.md` (files starting with `_` are ignored).
- Each file has front matter (id, title, focus) and then questions written EXACTLY as:
    ### Q<number> [basic|intermediate|advanced|design] Question text
    answer body in Markdown (paragraphs, bullets, tables, fenced code, **bold**, `code`)
- Optional intro text between the front matter and Q1.

DELIVERABLES
1. `build_site.py` (Python 3 standard library only) that:
   - parses all topic files,
   - writes ONE self-contained `index.html` (no CDN, no external fonts, works offline, light/dark),
   - writes `QUESTION_INDEX.md` (table of counts per topic/level + every question as a bullet),
   - prints a validation report and warns when a topic has fewer than 15 or more than 25 questions.
2. `index.html` features:
   - sidebar of topics with question counts,
   - full-text search across questions and answers,
   - level filter (basic / intermediate / advanced / design),
   - collapsible answers, Expand/Collapse all,
   - "Hide answers" self-test mode, "Mock: random 10" mode,
   - per-question "I can answer this confidently" checkbox saved in localStorage with a progress counter,
   - mobile friendly.
3. `README.md`: how to add a topic, how to build, how to deploy (GitHub Pages).
4. Optional `examples/<topic>/` folder with runnable code that a question can reference.

RULES
- No frameworks, no build tooling beyond Python. No network calls at runtime.
- Never put personal data in topic files; the repo must be reusable by anyone.
- Keep the Q-heading regex strict so malformed questions are reported, not silently skipped.
- After building, run it, show the per-topic counts, and fix any topic outside 15-25 questions.

OPTIONAL UPGRADE (only if asked)
- Add `examples/` runner: a "Run" button per code sample using a local server that executes
  the file and streams logs to the page (VS Code / localhost only).
```

---

## Prompt B - Generate a new topic file

```
Create `topics/<nn>-<slug>.md` for the topic: <TOPIC>.
Target role: <e.g. Lead Java Developer, 10+ years>. Company type: <product / service / fintech>.
My experience with this topic: <none | basic | hands-on> and the stack I used: <list>.

Write 15 to 25 questions ordered basic -> intermediate -> advanced -> design.
Use EXACTLY this heading format:  ### Q<n> [basic|intermediate|advanced|design] <question>

For every question:
- First sentence answers the question directly, in simple language (no jargon without a one-line explanation).
- Then: why it exists, how it works, trade-off or "when NOT to use it", and a real production example.
- Add a small code or config sample only when it removes confusion.
- Add one "> Follow-up they may ask:" line for intermediate/advanced questions.

Include:
- at least 3 design / architecture-level questions (requirements -> approach -> components -> trade-offs -> failure modes),
- at least 2 production-troubleshooting questions ("X is slow / failing - how do you debug?"),
- 2 questions that are currently trending for this topic (name the version/year),
- if my experience is "none/basic": add an honest-answer question showing how to answer
  ("I have not run X in production, but I understand ... and I have done the equivalent with Y").

Do not repeat questions that exist in other topic files. Keep answers 3-10 lines unless depth is needed.
After writing, run `python3 build_site.py` and fix any format errors.
```

---

## Prompt C - Tailor topics to a resume (optional)

```
Read my resume. List the technologies I have actually used in production.
For each, create or extend a topic file so that at least 3 questions per topic
are phrased the way an interviewer would probe MY project experience
("In your <project>, how did you handle <problem>?") with a model answer skeleton
(Situation -> Decision -> Trade-off -> Result) that I can fill with my real numbers.
Ignore technologies I marked as not wanted.
```
