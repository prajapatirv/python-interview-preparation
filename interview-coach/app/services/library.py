"""The content library: stacks -> topics -> questions, documents and examples.

Everything is driven by files, so adding content never needs a code change:

- ``skills/<stack>/_persona.md``  — the stack: title, ``content`` root, mixed-topic ``guides``, the
  Python ``index``, files to ``ignore``; the body is the AI persona.
- ``skills/<stack>/NN_*.md``      — one topic ("skill"): ``crib`` sheets, deep-dive ``docs``,
  ``examples`` folder, ``folders`` (for the Python index), ``keywords`` (for classifying guide
  questions); the body is the AI instruction pack for that topic.
- ``<content>/interview-scenarios/*.md`` — scenario banks, attached to a topic by front-matter ``skill:``.

Every question carries a ``kind`` saying where it came from:

=========  ==================================================  =====================
kind       source                                              topic assignment
=========  ==================================================  =====================
scenario   interview-scenarios/*.md                             ``skill:`` front matter
crib       topics/*.md (Java crib sheets)                       the skill file lists it
deepdive   deep_dive/*.md "Interview questions" sections        the skill file lists it
guide      the Java Q&A guides (mixed topics)                   keyword classification
index      the Python QUESTION_INDEX.md                         folder number, else keywords
=========  ==================================================  =====================

``coverage()`` lists every Markdown file under each content root that contains questions and says
whether it is wired in — the guarantee that no existing question is silently left out.
"""
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .. import config
from . import bank

EXAMPLE_SUFFIXES = (".java", ".py")
# Sources without their own level label get "mid" — an honest middle, not a claim of seniority.
KIND_LEVEL_DEFAULT = {"deepdive": "mid", "guide": "mid", "index": "mid", "crib": "mid", "scenario": "mid"}
SKIP_DIRS = {".venv", "node_modules", "legacy_examples", "__pycache__", ".pytest_cache"}
# Files that contain question-shaped headings but are not question banks.
NOT_BANKS = {"README.md", "APP_BUILD_PROMPT.md", "java_interview_app_prompts.md", "_TEMPLATE.md", "PLAN.md"}


@dataclass
class Topic:
    stack: str
    id: str
    title: str
    order: int
    summary: str
    instructions: str
    crib: list[str]
    docs: list[str]
    examples: str
    folders: list[str]
    keywords: list[str]
    scenario_files: list[str] = field(default_factory=list)
    questions: list[dict] = field(default_factory=list)


@dataclass
class Stack:
    id: str
    title: str
    order: int
    tagline: str
    content: str
    persona: str
    guides: list[str]
    index: str
    ignore: list[str]
    topics: list[Topic] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)      # every file questions were read from


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _doc_title(path: Path) -> str:
    """Front-matter ``title:`` (crib sheets), else the first ``# `` heading, else the file name."""
    try:
        meta, body = bank.parse_front_matter(path.read_text(encoding="utf-8"))
    except OSError:
        return path.stem
    if meta.get("title"):
        return meta["title"] + (" (crib sheet)" if "/topics/" in path.as_posix() else "")
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _kw_hits(text: str, keywords: list[str]) -> int:
    text = f" {text.lower()} "
    return sum(1 for k in keywords if re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", text))


def classify(topics: list[Topic], title: str, section: str = "") -> Topic:
    """Best topic for a question from a mixed guide: keyword hits in the title count double the section's."""
    best, best_score = None, 0
    for t in topics:
        if not t.keywords:
            continue
        score = 2 * _kw_hits(title, t.keywords) + _kw_hits(section, t.keywords)
        if score > best_score:
            best, best_score = t, score
    return best or next((t for t in topics if t.id == "general"), topics[-1])


def _level_from_section(section: str, default: str) -> str:
    s = section.lower()
    if "fresher" in s or "basic" in s:
        return "fresher"
    if "experienced" in s or "advanced" in s or "scenario" in s:
        return "senior"
    return default


class Library:
    def __init__(self, stacks: list[Stack], root: Path):
        self.stacks = stacks
        self.root = root
        self._by_id = {q["id"]: q for s in stacks for t in s.topics for q in t.questions}

    # ------------------------------------------------------------------ loading
    @classmethod
    def load(cls) -> "Library":
        root, skills = config.WORKSPACE_ROOT, config.SKILLS_DIR
        stacks = []
        for d in sorted(p for p in skills.iterdir() if p.is_dir()) if skills.is_dir() else []:
            persona_file = d / "_persona.md"
            if not persona_file.is_file():
                continue
            meta, persona = bank.parse_front_matter(_read(persona_file))
            stack = Stack(id=meta.get("stack", d.name), title=meta.get("title", d.name.title()),
                          order=int(meta.get("order", 99)), tagline=meta.get("tagline", ""),
                          content=meta.get("content", ""), persona=persona.strip(),
                          guides=[p for p in bank.split_list(meta.get("guides")) if (root / p).is_file()],
                          index=meta.get("index", "") if (root / meta.get("index", "-")).is_file() else "",
                          ignore=bank.split_list(meta.get("ignore")))
            for f in sorted(d.glob("[0-9]*.md")):
                tm, body = bank.parse_front_matter(_read(f))
                stack.topics.append(Topic(
                    stack=stack.id, id=tm.get("id", f.stem), title=tm.get("title", f.stem),
                    order=int(tm.get("order", 99)), summary=tm.get("summary", ""), instructions=body.strip(),
                    crib=[p for p in bank.split_list(tm.get("crib")) if (root / p).is_file()],
                    docs=[p for p in bank.split_list(tm.get("docs")) if (root / p).is_file()],
                    examples=tm.get("examples", ""), folders=bank.split_list(tm.get("folders")),
                    keywords=[k.lower() for k in bank.split_list(tm.get("keywords"))]))
            stack.topics.sort(key=lambda t: (t.order, t.id))
            if stack.topics:
                cls._load_questions(stack, root)
            stacks.append(stack)
        stacks.sort(key=lambda s: (s.order, s.id))
        return cls(stacks, root)

    @classmethod
    def _load_questions(cls, stack: Stack, root: Path) -> None:
        topics = {t.id: t for t in stack.topics}
        # scenario banks attach themselves by front matter
        bank_dir = root / stack.content / "interview-scenarios"
        for f in sorted(bank_dir.glob("*.md")) if stack.content and bank_dir.is_dir() else []:
            meta, _, qs = bank.parse_questions(_read(f))
            t = topics.get(meta.get("skill", "")) or topics.get("general") or stack.topics[-1]
            rel = _rel(f, root)
            t.scenario_files.append(rel)
            cls._add(stack, t, qs, rel, "scenario")
        for t in stack.topics:
            for rel in t.crib:
                cls._add(stack, t, bank.parse_questions(_read(root / rel))[2], rel, "crib")
            for rel in t.docs:
                cls._add(stack, t, bank.parse_questions(_read(root / rel))[2], rel, "deepdive")
        for rel in stack.guides:
            for q in bank.parse_questions(_read(root / rel))[2]:
                t = classify(stack.topics, q["title"], q["section"])
                q["level"] = q["level"] or _level_from_section(q["section"], "mid")
                cls._add(stack, t, [q], rel, "guide", count_source=False)
            stack.sources.append({"path": rel, "kind": "guide",
                                  "questions": sum(1 for t in stack.topics for q in t.questions if q["source"] == rel)})
        if stack.index:
            by_folder = {f[:2]: t for t in stack.topics for f in t.folders}
            for q in bank.parse_index(_read(root / stack.index)):
                num = q["section"][:2]
                t = by_folder.get(num) if num.isdigit() else None
                t = t or classify(stack.topics, q["title"], q["section"])
                cls._add(stack, t, [q], stack.index, "index", count_source=False)
            stack.sources.append({"path": stack.index, "kind": "index",
                                  "questions": sum(1 for t in stack.topics for q in t.questions
                                                   if q["source"] == stack.index)})
        cls._rehome_misfiled(stack)
        cls._merge_foundations(stack)

    @classmethod
    def _rehome_misfiled(cls, stack: Stack) -> None:
        """The coding deep dive also holds Spring/REST questions (DI, JWT, auto-configuration...). Re-classify
        its deep-dive questions by keyword so they show under the topic they belong to, not 'Coding round'."""
        coding = next((t for t in stack.topics if t.id == "coding"), None)
        if coding is None:
            return
        keep = []
        for q in coding.questions:
            if q["kind"] != "deepdive" or not q["title"].startswith("(V. IMP.)"):
                keep.append(q)       # real coding problems stay; only the '(V. IMP.)' Spring/REST cards move
                continue
            dest = classify([t for t in stack.topics if t.id not in ("general", "leadership", "coding")],
                            q["title"], q["section"])
            if re.search(r"\b(Spring|Bean\w*|ApplicationContext|Singleton scope)\b", q["title"]):
                dest = next((t for t in stack.topics if t.id == "spring-boot"), dest)
            if dest is not None and dest.id not in ("coding", "general"):
                q["topic"] = dest.id
                dest.questions.append(q)
            else:
                keep.append(q)
        coding.questions = keep

    @staticmethod
    def _norm_title(title: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()

    @classmethod
    def _merge_foundations(cls, stack: Stack) -> None:
        """A short crib/guide/deep-dive card shows the concepts-first answer when one exists for the same question
        (matched on the normalised title), so the full explanation needs no AI. The original short answer is kept
        as the last section, and ``body`` is untouched so AI prompts and the checker still see it."""
        found = {}
        for t in stack.topics:
            for q in t.questions:
                if q["kind"] == "scenario" and any(s["key"] == "concepts" for s in q["sections"]):
                    found.setdefault(cls._norm_title(q["title"]), q)
        for t in stack.topics:
            for q in t.questions:
                src = found.get(cls._norm_title(q["title"]))
                if q["kind"] == "scenario" or src is None or any(s["key"] == "concepts" for s in q["sections"]):
                    continue
                own = q["sections"] or [{"key": "original", "label": "Original short answer", "md": q["body"]}]
                q["sections"] = [dict(s) for s in src["sections"]] + own
                q["foundation_id"] = src["id"]

    @staticmethod
    def _add(stack: Stack, t: Topic, qs: list[dict], rel: str, kind: str, count_source: bool = True) -> None:
        for q in qs:
            q.update(kind=kind, stack=stack.id, topic=t.id, source=rel,
                     level=q["level"] or KIND_LEVEL_DEFAULT[kind],
                     id=bank.stable_id(stack.id, rel, q["label"], q["title"]))
            t.questions.append(q)
        if count_source:
            stack.sources.append({"path": rel, "kind": kind, "topic": t.id, "questions": len(qs)})

    # ------------------------------------------------------------------ queries
    def stack(self, stack_id: str) -> Stack | None:
        return next((s for s in self.stacks if s.id == stack_id), None)

    def topic(self, stack_id: str, topic_id: str) -> Topic | None:
        s = self.stack(stack_id)
        return next((t for t in s.topics if t.id == topic_id), None) if s else None

    def question(self, qid: str) -> dict | None:
        return self._by_id.get(qid)

    def questions(self, stack_id: str, topic_id: str | None = None) -> list[dict]:
        s = self.stack(stack_id)
        if not s:
            return []
        return [q for t in s.topics if topic_id in (None, "", t.id) for q in t.questions]

    def summary(self) -> list[dict]:
        out = []
        for s in self.stacks:
            topics = []
            for t in s.topics:
                kinds = {}
                for q in t.questions:
                    kinds[q["kind"]] = kinds.get(q["kind"], 0) + 1
                topics.append({"id": t.id, "title": t.title, "summary": t.summary,
                               "total": len(t.questions), "kinds": kinds, "docs": len(t.docs)})
            out.append({"id": s.id, "title": s.title, "tagline": s.tagline, "topics": topics,
                        "total": sum(t["total"] for t in topics)})
        return out

    def topic_detail(self, t: Topic) -> dict:
        ex_dir = self.root / t.examples if t.examples else None
        examples = sorted(p.name for p in ex_dir.iterdir() if p.suffix in EXAMPLE_SUFFIXES) \
            if ex_dir and ex_dir.is_dir() else []
        return {"id": t.id, "stack": t.stack, "title": t.title, "summary": t.summary,
                "questions": t.questions, "scenario_files": t.scenario_files,
                "docs": [{"path": p, "title": _doc_title(self.root / p)} for p in t.docs + t.crib],
                "examples": {"folder": t.examples, "files": examples}}

    def allowed_doc(self, path: str) -> Path | None:
        """Only Markdown files that the library itself reads are served (no path traversal)."""
        allowed = {src["path"] for s in self.stacks for src in s.sources}
        allowed |= {p for s in self.stacks for t in s.topics for p in t.docs + t.crib}
        if path not in allowed:
            return None
        full = (self.root / path).resolve()
        return full if full.is_file() and self.root in full.parents else None

    def coverage(self) -> dict:
        """Every question-bearing Markdown file under each content root, and whether it is wired in."""
        report = []
        for s in self.stacks:
            used = {src["path"] for src in s.sources}
            content = self.root / s.content
            unreferenced = []
            for f in sorted(content.rglob("*.md")) if s.content and content.is_dir() else []:
                if SKIP_DIRS & set(f.relative_to(content).parts) or f.name in NOT_BANKS:
                    continue
                rel = _rel(f, self.root)
                if rel in used or rel in s.ignore:
                    continue
                text = _read(f)
                n = len(bank.parse_questions(text)[2]) or len(bank.parse_index(text))
                if n:
                    unreferenced.append({"path": rel, "questions": n})
            by_kind: dict[str, int] = {}
            for q in self.questions(s.id):
                by_kind[q["kind"]] = by_kind.get(q["kind"], 0) + 1
            # answer depth: questions whose answer starts from the concepts, and the shallow ones still without it
            titles = {q["title"].strip().lower() for q in self.questions(s.id)
                      if any(x["key"] == "concepts" for x in q.get("sections", []))}
            shallow = [q for q in self.questions(s.id) if q["kind"] in ("crib", "guide", "index")
                       and len(q["body"].split()) < 60 and q["title"].strip().lower() not in titles]
            depth = {"with_concepts": len(titles), "shallow_without_concepts": len(shallow),
                     "shallow_by_topic": {}}
            for q in shallow:
                depth["shallow_by_topic"][q["topic"]] = depth["shallow_by_topic"].get(q["topic"], 0) + 1
            report.append({"stack": s.id, "total": sum(by_kind.values()), "by_kind": by_kind, "depth": depth,
                           "sources": sorted(s.sources, key=lambda x: x["path"]),
                           "ignored": s.ignore, "unreferenced": unreferenced})
        return {"stacks": report}

    # ------------------------------------------------------------------ writing
    def save_question(self, stack_id: str, topic_id: str, level: str, title: str, body: str,
                      tags: list[str]) -> str:
        """Appends a question to the topic's first scenario bank (creating one if needed). Returns its path."""
        s, t = self.stack(stack_id), self.topic(stack_id, topic_id)
        if not s or not t or not s.content:
            raise ValueError("unknown stack or topic")
        if t.scenario_files:
            path = self.root / t.scenario_files[0]
            existing = _read(path)
        else:
            path = self.root / s.content / "interview-scenarios" / f"{t.order + 50:02d}_{t.id.replace('-', '_')}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            existing = (f"---\nid: {t.id}\ntitle: {t.title}\nstack: {s.id}\nskill: {t.id}\n---\n"
                        "Scenario answers saved from the Interview Coach. Review each one before relying on it.\n")
        _, _, qs = bank.parse_questions(existing)
        num = max((q["num"] for q in qs), default=0) + 1
        level = bank.normalise_level(level)
        title = re.sub(r"\s+", " ", title).strip()
        text = existing.rstrip("\n") + "\n\n" + bank.render_question(num, level, title, body, tags)
        path.write_text(text, encoding="utf-8")
        return _rel(path, self.root)


    def add_alternative(self, question_id: str, angle: str, body: str) -> str:
        """Writes an approved alternative answer into the question's own source file. Returns its path."""
        q = self.question(question_id)
        if q is None or q["kind"] != "scenario":
            raise ValueError("alternatives can only be added to scenario questions")
        if any(a["md"].strip() == body.strip() for a in bank.alternatives(q)):
            raise ValueError("this alternative is already in the bank")
        path = self.root / q["source"]
        path.write_text(bank.insert_into_question(_read(path), q["label"], q["title"],
                                                  bank.render_alternative(angle, body)), encoding="utf-8")
        return q["source"]


class LibraryHolder:
    """Lets /api/reload swap the library atomically while requests keep reading the old one."""

    def __init__(self):
        self._lock = threading.Lock()
        self._lib = Library.load()

    @property
    def lib(self) -> Library:
        return self._lib

    def reload(self) -> Library:
        lib = Library.load()
        with self._lock:
            self._lib = lib
        return lib
