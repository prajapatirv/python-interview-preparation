"""Parses every question format in the content repos into structured questions.

Heading-based formats (``parse_questions``) — a question runs until the next heading of the same or a
higher level:

- **scenario banks** ``### Q<n> [level] text`` + ``tags:`` line + ``**Section**`` labels
  (``*/interview-scenarios/*.md``).
- **crib sheets** ``### Q<n> [basic|intermediate|advanced|design] text`` (``java-interview-prep/topics``).
- **deep dives** ``### Q<n>. text`` under "Interview questions and full answers" (both repos' ``deep_dive``).
- **guides** ``## Q<n>. text`` / ``## A<n>. text`` under ``# Section`` headings (the Java Q&A guides);
  the parent heading is kept as ``section`` so the library can classify the question into a topic.

Bullet-based format (``parse_index``): the Python ``QUESTION_INDEX.md``
(``- **Q:** question`` / ``**A:** answer`` under ``### NN — Folder`` headings).
"""
import hashlib
import re

LEVELS = ["fresher", "mid", "senior", "architect"]
LEVEL_ALIASES = {"basic": "fresher", "intermediate": "mid", "advanced": "senior", "design": "architect",
                 "junior": "fresher", "lead": "architect", "staff": "architect"}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
# "Q12 [senior] text", "Q12. text", "A3. text" - a capital letter, digits, then [level] or "." or ":"
Q_RE = re.compile(r"^([A-Z])(\d+)(?:\s*\[([\w-]+)\]|[.:])\s*(.+)$")
INDEX_Q_RE = re.compile(r"^\s*-\s+\*\*Q:\*\*\s*(.*)$")
INDEX_A_RE = re.compile(r"^\s*\*\*A:\*\*\s*(.*)$")
SECTION_RE = re.compile(r"^\*\*([^*]+?)\*\*\s*(?:\(.*\))?\s*$")
TAGS_RE = re.compile(r"^tags:\s*(.*)$", re.I)

# Canonical keys for the scenario sections, matched on a prefix of the label.
SECTION_KEYS = [
    ("the live scenario", "scenario"), ("what the interviewer", "probe"), ("how i answer", "answer"),
    ("trade-offs", "tradeoffs"), ("how i'd monitor", "monitoring"), ("how i would monitor", "monitoring"),
    ("numbers i quote", "numbers"), ("follow-ups", "followups"), ("60-second", "spoken"),
    ("minimal config", "config"),
]


def normalise_level(raw: str | None, default: str = "mid") -> str:
    raw = (raw or "").lower()
    return raw if raw in LEVELS else LEVEL_ALIASES.get(raw, default)


def stable_id(*parts: str) -> str:
    """Short id that survives re-ordering a file (progress in the browser is keyed on it)."""
    return hashlib.sha1("\u0000".join(parts).encode("utf-8")).hexdigest()[:12]


def section_key(label: str) -> str:
    low = label.lower().strip()
    for prefix, key in SECTION_KEYS:
        if low.startswith(prefix):
            return key
    return re.sub(r"[^a-z0-9]+", "-", low).strip("-") or "notes"


def parse_front_matter(text: str) -> tuple[dict, str]:
    """``---``-fenced ``key: value`` lines. Comma lists stay strings; callers split what they need."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    meta = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, text[end + 4:].lstrip("\n")


def split_list(value: str) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def parse_questions(text: str) -> tuple[dict, str, list[dict]]:
    """Returns (front matter, intro markdown, questions). Each question:
    ``{num, label, level (None if the source has none), title, section, tags, sections, body}``.
    ``sections`` holds the ``**Label**`` blocks of scenario answers and is empty for free-form answers."""
    meta, body = parse_front_matter(text)
    intro, questions, cur = [], [], None
    parents: dict[int, str] = {}                  # heading depth -> text, for the "section" context
    in_fence = False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        h = None if in_fence else HEADING_RE.match(line)
        if h:
            depth, htext = len(h.group(1)), h.group(2)
            m = Q_RE.match(htext)
            if m:
                cur = {"num": int(m.group(2)), "label": m.group(1) + m.group(2),
                       "level": normalise_level(m.group(3)) if m.group(3) else None,
                       "title": m.group(4).strip(), "depth": depth,
                       "section": next((parents[d] for d in range(depth - 1, 0, -1) if d in parents), ""),
                       "tags": [], "lines": []}
                questions.append(cur)
                continue
            parents = {d: t for d, t in parents.items() if d < depth}
            parents[depth] = htext
            if cur is not None and depth <= cur["depth"]:
                cur = None                            # a sibling/parent heading ends the question
        if cur is None:
            if not questions:
                intro.append(line)
        else:
            cur["lines"].append(line)
    for q in questions:
        _finish(q)
    return meta, "\n".join(intro).strip(), questions


def parse_index(text: str) -> list[dict]:
    """The bullet format of the Python QUESTION_INDEX.md. ``group`` is the nearest ``###`` heading."""
    out, cur, group, mode = [], None, "", None
    for line in text.replace("\r\n", "\n").split("\n"):
        h = HEADING_RE.match(line)
        if h:
            group, cur = h.group(2), None
            continue
        if m := INDEX_Q_RE.match(line):
            cur = {"num": len(out) + 1, "label": f"Q{len(out) + 1}", "level": None, "title": m.group(1).strip(),
                   "section": group, "tags": [], "sections": [], "answer": []}
            out.append(cur)
            mode = "q"
            continue
        if cur is None:
            continue
        if m := INDEX_A_RE.match(line):
            mode = "a"
            cur["answer"].append(m.group(1))
        elif line.startswith("**") or not line.strip():
            cur, mode = (None, None) if line.startswith("**") else (cur, mode)
        elif mode == "q":
            cur["title"] += " " + line.strip()
        else:
            cur["answer"].append(line.strip())
    for q in out:
        q["body"] = "\n".join(q.pop("answer")).strip()
    return out


def _finish(q: dict) -> None:
    q.pop("depth", None)
    lines = q.pop("lines")
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and (t := TAGS_RE.match(lines[0])):
        q["tags"] = [s.strip().lower() for s in t.group(1).split(",") if s.strip()]
        lines.pop(0)
    # a trailing horizontal rule belongs to the file layout, not the answer
    while lines and lines[-1].strip() in ("", "---"):
        lines.pop()
    q["body"] = "\n".join(lines).strip()
    sections, cur, in_fence = [], None, False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else SECTION_RE.match(line)
        if m:
            cur = {"key": section_key(m.group(1)), "label": m.group(1).strip(), "lines": []}
            sections.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
    for s in sections:
        s["md"] = "\n".join(s.pop("lines")).strip()
    q["sections"] = sections


def section(q: dict, key: str) -> str:
    return next((s["md"] for s in q.get("sections", []) if s["key"] == key), "")


def followups(q: dict) -> list[str]:
    """The interviewer follow-up questions listed in a scenario answer (``- *question* -> answer``)."""
    out = []
    for line in section(q, "followups").splitlines():
        m = re.match(r"^\s*[-*]\s+\*(.+?)\*", line)
        if m:
            out.append(m.group(1).strip())
    return out


def render_question(num: int, level: str, title: str, body: str, tags: list[str]) -> str:
    """Markdown for one question in bank format (used when saving a generated question)."""
    head = f"### Q{num} [{level}] {title.strip()}\n"
    if tags:
        head += "tags: " + ", ".join(tags) + "\n"
    return head + "\n" + body.strip() + "\n"
