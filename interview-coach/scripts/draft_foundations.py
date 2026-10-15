"""Draft concepts-first ("from the basics") answers for shallow questions, using the Claude API.

    .venv/Scripts/python.exe scripts/draft_foundations.py --dry-run
    .venv/Scripts/python.exe scripts/draft_foundations.py --topic java-core --limit 25
    .venv/Scripts/python.exe scripts/draft_foundations.py --topic all

A question is "shallow" when it is a crib/guide/index answer under ``--max-words`` words and no scenario entry
with a ``Start here: the concepts`` section already carries its title. Drafts are appended to
``<content root>/interview-scenarios/<NN>_<topic>_foundations.md`` in the machine-read bank format, so the coach
picks them up with no code change. Re-running resumes: titles already drafted are skipped.

Drafts are model output: review them (PLAN_ANSWER_QUALITY.md, action J11) before relying on them.
"""
import argparse
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.services import ai, bank, library  # noqa: E402

ORDER = ["java-core", "spring-boot", "kafka", "rest-api", "microservices", "nosql", "performance", "production",
         "splunk-observability", "sql", "architecture", "testing", "cloud-devops"]
SKIP = {"coding", "general"}
FILE_NUM = {t: 20 + i for i, t in enumerate(ORDER)}
FILE_NUM["leadership"] = 40
BEHAVIORAL = {"leadership"}                       # drafted as frameworks + labelled illustrative examples
REQUIRED = {"concepts", "scenario", "probe", "answer", "tradeoffs", "spoken"}

FORMAT = """Write the answer in EXACTLY this Markdown structure and nothing else (no preamble, no closing remark):

tags: <4-7 lowercase comma-separated tags>, basics

**Start here: the concepts**
<bullets: define every technical term the answer needs in one or two plain sentences each, from first principles,
as if to a smart person who has never met the term. Say why the thing exists.>

**The live scenario**
<a concrete production story with numbers: what the team saw, what went wrong or why the choice mattered>

**What the interviewer is really checking**
<one or two sentences>

**How I answer it**
<numbered steps. Each step states the rule AND the reason. Explain the logic and mechanism in simple language.
At most one short code or config snippet, only if it truly clarifies.>

**Trade-offs and what can go wrong**
<short paragraph or bullets: costs, pitfalls, common mistakes>

**How I'd monitor it**
<the metrics, tools or checks that prove it in practice>

**Follow-ups to expect**
- *<follow-up question>* -> <short strong answer>
- *<follow-up question>* -> <short strong answer>

**60-second answer**
<the answer as you would say it aloud, in plain words, 4-6 sentences>

Rules: simple language, no unexplained jargon, no marketing tone, do not invent library versions or numbers you
are not sure of (use clearly illustrative numbers in the scenario), keep the whole answer under 700 words."""

BEHAVIORAL_CONTEXT = """How leading companies run behavioural and leadership interviews (use only these facts, say nothing else about them):
- Amazon: answers are judged against the 16 Leadership Principles using real past stories; a bar-raiser interviewer from another team can veto; use "I" not "we"; be specific and data-driven; prepare 3-4 flexible STAR stories; failure questions are common.
- Google: four attributes (general cognitive ability, leadership, role-related knowledge, "Googleyness"); the leadership bar is emergent leadership: step up when needed, step back when not; STAR plus L (Learning); keep Situation short, spend time on your Action, quantify the Result.
- Atlassian: a dedicated values interview against five values (Open company no bullshit; Build with heart and balance; Don't #@!% the customer; Play, as a team; Be the change you seek); conflict and compromise questions are typical.
- Meta: standardised rubrics; a dedicated project-retrospective slot.
- Indian service/product firms (Infosys, EPAM, similar): a managerial round that asks about production issues you solved, conflict, estimation, mentoring and ownership.
- Senior engineers are scored on judgement: what you did after a decision went against you, what changed your mind, how you made others better."""

BEHAVIORAL_FORMAT = """Write the answer in EXACTLY this Markdown structure and nothing else (no preamble):

tags: <4-7 lowercase comma-separated tags>, behavioural, leadership

**Start here: the concepts**
<bullets in plain words: what competency this question tests, what the interviewer is trying to learn, and which
company frameworks it maps to (use only the facts given). Define the answer structure (STAR plus Learning).>

**The live scenario**
<how this question is actually asked in a round, with two or three typical phrasings, and what the interviewer
writes down>

**What the interviewer is really checking**
<one or two sentences, in terms of signals: ownership, judgement, communication, learning>

**How I answer it**
<numbered steps for building a strong answer: what to pick as a story, how long to spend on each part, what to
quantify. Then a MODEL ANSWER of 120-170 words, spoken in first person, built on an ILLUSTRATIVE example from
a Java/Spring/Kafka backend team, introduced by the exact words "Illustrative example (replace with your own
story):". Use [square brackets] for numbers the candidate must fill in with their own facts.>

**Trade-offs and what can go wrong**
<the common weak answers and red flags, and why they fail; one honest note on what not to exaggerate>

**Your story prompt**
<three or four questions the candidate should ask themselves to find a real story from their own work>

**Follow-ups to expect**
- *<follow-up question>* -> <what a strong answer covers>
- *<follow-up question>* -> <what a strong answer covers>

**60-second answer**
<a spoken template with [placeholders] for the candidate's own facts, 5-6 sentences>

Rules: simple language, no clichés like "passionate" or "synergy", never invent facts about the candidate, keep it
under 700 words."""


def shallow(lib, topic, max_words):
    have = {x["title"].strip().lower() for t in lib.stack("java").topics for x in t.questions
            if any(s["key"] == "concepts" for s in x.get("sections", []))}
    out = []
    for q in topic.questions:
        if q["kind"] not in ("crib", "guide", "index"):
            continue
        if len(q["body"].split()) >= max_words or q["title"].strip().lower() in have:
            continue
        out.append(q)
    return out


async def draft(client, stack, topic, q, sem, retries=1):
    system = ai.system_prompt(stack, topic)
    head = (f"Candidate level: {q['level']}\n<question>{q['title']}</question>\n"
            f"<stored_answer>\n{q['body'][:3000]}\n</stored_answer>\n\n")
    if topic.id in BEHAVIORAL:
        system += "\n\n" + BEHAVIORAL_CONTEXT
        prompt = (head + "Turn this into a complete coaching answer for a senior Java backend candidate. Keep the "
                  "facts in the stored answer. The candidate's own stories are NOT known.\n"
                  "HONESTY RULES (strict): (1) Some questions are about the candidate's own project or "
                  "experience. State in first person ONLY facts that appear in the stored answer. "
                  "(2) Never invent the candidate's team size, counts, percentages, incidents, dates or results. "
                  "Any such detail must be a [placeholder] for the candidate to fill in, or sit inside a scenario "
                  "that begins with the words 'Illustrative scenario (not your project):' and is written in the "
                  "third person ('a team'), never 'we' or 'our'. (3) The 60-second answer may use 'I' or 'we' "
                  "only for facts from the stored answer; everything else is a [placeholder]. (4) If the "
                  "question is technical (a library or framework), keep it accurate and teach it from the "
                  "basics.\n\n" + BEHAVIORAL_FORMAT)
    else:
        prompt = (head + "The stored answer is too dense: it assumes the reader already knows the vocabulary. "
                  "Rewrite it as a complete teaching answer. Keep every fact in the stored answer, correct "
                  "anything wrong, and add what a learner needs to truly understand it. If the question asks "
                  "about the candidate's own experience, never invent personal facts: use third person for the "
                  "scenario and label any numbers illustrative.\n\n" + FORMAT)
    level = bank.normalise_level(q.get("level"), "mid")
    for attempt in range(retries + 1):
        async with sem:
            resp = await client.messages.create(
                model=config.ANTHROPIC_MODEL, max_tokens=3500,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        text = re.sub(r"^```(?:markdown)?\n|\n```$", "", text).strip()
        _, _, qs = bank.parse_questions(f"### Q1 [{level}] {q['title']}\n{text}\n")
        keys = {s["key"] for s in qs[0]["sections"]} if qs else set()
        if qs and not (REQUIRED - keys) and len(text.split()) >= 200:
            return level, text
        print(f"  retry: {q['title'][:60]!r} missing {sorted(REQUIRED - keys)}", flush=True)
    return None


async def run(args):
    lib = library.Library.load()
    stack = lib.stack("java")
    root = config.WORKSPACE_ROOT / "java" / "java-interview-prep" / "interview-scenarios"
    topics = ORDER if args.topic == "all" else [t.strip() for t in args.topic.split(",")]
    plan = []
    for tid in topics:
        topic = lib.topic("java", tid)
        if topic is None or tid in SKIP:
            print(f"skip {tid}")
            continue
        qs = shallow(lib, topic, args.max_words)
        if args.limit:
            qs = qs[:args.limit]
        plan.append((topic, qs))
        print(f"{tid:22s} {len(qs):3d} shallow questions to draft")
    if args.dry_run:
        return
    import anthropic
    client = anthropic.AsyncAnthropic()
    sem = asyncio.Semaphore(args.workers)
    for topic, qs in plan:
        if not qs:
            continue
        path = root / f"{FILE_NUM.get(topic.id, 40)}_{topic.id.replace('-', '_')}_foundations.md"
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        done = {m.strip().lower() for m in re.findall(r"^### Q\d+ \[\w+\] (.+)$", existing, re.M)}
        todo = [q for q in qs if q["title"].strip().lower() not in done]
        if not existing:
            existing = (f"---\nid: foundations-{topic.id}\ntitle: {topic.title}: from the basics (drafted)\n"
                        f"stack: java\nskill: {topic.id}\n---\nDrafted concepts-first answers for questions whose "
                        "stored answer was too short. Each starts with the concepts in plain words, then a real "
                        "scenario, then the answer. Review before relying on them.\n\n"
                        "Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).\n")
        n = len(re.findall(r"^### Q\d+ ", existing, re.M))
        print(f"== {topic.id}: drafting {len(todo)} -> {path.name}", flush=True)
        results = await asyncio.gather(*[draft(client, stack, topic, q, sem) for q in todo], return_exceptions=True)
        added = 0
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(existing.rstrip("\n") + "\n")
            for q, r in zip(todo, results):
                if isinstance(r, Exception) or r is None:
                    print(f"  FAILED: {q['title'][:70]!r} {r if isinstance(r, Exception) else ''}", flush=True)
                    continue
                level, text = r
                n += 1
                added += 1
                f.write(f"\n### Q{n} [{level}] {q['title'].strip()}\n{text}\n")
        print(f"   wrote {added}/{len(todo)}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--topic", default="all", help="topic id, comma list, or all")
    ap.add_argument("--limit", type=int, default=0, help="max questions per topic (0 = all)")
    ap.add_argument("--max-words", type=int, default=60, help="answers shorter than this are 'shallow'")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.dry_run and ai.mode() != "claude":
        print("No API key found: set ANTHROPIC_API_KEY in interview-coach/.env", file=sys.stderr)
        return 1
    asyncio.run(run(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
