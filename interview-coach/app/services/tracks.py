"""Experience tracks: turn the whole bank into a short study plan for one level of experience.

A track is data, not code (``skills/<stack>/_tracks.json``): which topics matter at this level, how much weight each
has, and how many questions to take at each level. ``plan`` selects them in a stable order:

- only ``kinds`` with trustworthy level labels are used (unlabelled sources just default to "mid"),
- anything matching ``exclude`` is left out: material about one person's own projects or one company's domain,
- questions candidates reported from real interviews come first, then scenario answers,
- sources take turns, so one big list can't fill a stage and narrow what gets studied,
- a question that repeats one already chosen is skipped, because the banks overlap on purpose.
"""
import json
import math
import re

from .. import config
from .library import Library

STAGE_ORDER = ["fresher", "mid", "senior", "architect"]
STAGE_LABEL = {"fresher": "Basics", "mid": "Applied", "senior": "Advanced", "architect": "Design"}
MINUTES_PER_QUESTION = 5
# Tags of questions reported from real rounds. "reported-genai" is left out: that pack is study material, not interviews.
REPORTED_TAGS = {"reported-rounds", "reported-streams", "jpmc", "nagarro", "virtusa", "deloitte", "persistent",
                 "epam", "mastercard", "capgemini"}
STOPWORDS = set("a an and are as at be but by can do does for from how i in is it its of on or the to vs what when where "
                "which why will with would you your explain describe difference between".split())
SIMILAR = 0.7        # shared words / all words: two titles saying nearly the same thing
CONTAINED = 0.9      # shared words / the shorter title: a short title restated inside a longer one


def load(stack_id: str) -> dict | None:
    path = config.SKILLS_DIR / stack_id / "_tracks.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def is_reported(q: dict) -> bool:
    return bool(REPORTED_TAGS & set(q["tags"])) or "_round_" in q["source"]


def _words(title: str) -> set[str]:
    words = (w.strip(".") for w in re.findall(r"[a-z0-9@+#.]+", title.lower()))
    return {w for w in words if w and w not in STOPWORDS}


def _head(title: str) -> str:
    """The subject of a question: "What is a consumer group, and what happens..." -> "consumer group"."""
    first = re.split(r",| and |\?", title.lower(), maxsplit=1)[0]
    return " ".join(sorted(_words(first), key=first.find))


def _repeats(title: str, seen: list[tuple[set[str], str]]) -> bool:
    words, head = _words(title), _head(title)
    if not words:
        return False
    for other, other_head in seen:
        shared = len(words & other)
        if shared / len(words | other) >= SIMILAR or shared / min(len(words), len(other)) >= CONTAINED:
            return True
        if len(min(head, other_head, key=len).split()) >= 2 and (head.startswith(other_head) or other_head.startswith(head)):
            return True
    return False


def _take_turns(pool: list[dict]) -> list[dict]:
    """Ranked questions, one from each source in turn. Sources keep their rank, so reported ones still lead."""
    by_source: dict[str, list[dict]] = {}
    for q in pool:
        by_source.setdefault(q["source"], []).append(q)
    out, queues = [], list(by_source.values())
    while queues:
        for queue in queues:
            out.append(queue.pop(0))
        queues = [q for q in queues if q]
    return out


def _rank(q: dict) -> tuple:
    return (not is_reported(q), q["kind"] != "scenario")


def plan(lib: Library, stack_id: str, track_id: str, added: set[str] | None = None, removed: set[str] | None = None) -> dict | None:
    """The study plan for one track. ``added``/``removed`` are the viewer's own topic changes."""
    cfg = load(stack_id)
    track = next((t for t in cfg["tracks"] if t["id"] == track_id), None) if cfg else None
    stack = lib.stack(stack_id)
    if track is None or stack is None:
        return None
    removed, added = removed or set(), added or set()
    focus = [f for f in track["focus"] if f["topic"] not in removed]
    known = {f["topic"] for f in track["focus"]}
    focus += [{"topic": t.id, "weight": "also", "why": "You added this topic."}
              for t in stack.topics if t.id in added and t.id not in known and t.id not in removed and t.questions]
    kinds = set(cfg["kinds"])
    excluded = [re.compile(x) for x in cfg.get("exclude", [])]
    seen: list[tuple[set[str], str]] = []
    stage_order = track.get("stage_order", STAGE_ORDER)
    topics = []
    for f in focus:
        topic = lib.topic(stack_id, f["topic"])
        if topic is None:
            continue
        chosen = []
        for level, base in track["quota"].items():
            want = math.ceil(base * cfg["weights"][f["weight"]])
            pool = _take_turns(sorted((q for q in topic.questions if q["kind"] in kinds and q["level"] == level
                                       and not any(x.search(q["source"]) or x.search(q["title"]) for x in excluded)), key=_rank))
            taken = 0
            for q in pool:
                if taken >= want:
                    break
                if _repeats(q["title"], seen):
                    continue
                seen.append((_words(q["title"]), _head(q["title"])))
                taken += 1
                chosen.append({"id": q["id"], "level": level, "reported": is_reported(q)})
        chosen.sort(key=lambda c: stage_order.index(c["level"]))
        topics.append({"id": topic.id, "title": topic.title, "weight": f["weight"], "why": f["why"], "questions": chosen})
    total = sum(len(t["questions"]) for t in topics)
    stages = {s: sum(1 for t in topics for q in t["questions"] if q["level"] == s) for s in STAGE_ORDER}
    return {"id": track["id"], "label": track["label"], "range": track["range"], "title": track["title"],
            "expect": track["expect"], "advice": track["advice"], "levels_reliable": cfg["levels_reliable"],
            "stage_label": STAGE_LABEL, "stage_order": stage_order, "stages": {s: n for s, n in stages.items() if n}, "topics": topics, "total": total,
            "hours": max(1, round(total * MINUTES_PER_QUESTION / 60)), "source_total": len(lib.questions(stack_id)),
            "other_topics": [{"id": t.id, "title": t.title} for t in stack.topics
                             if t.questions and t.id != "general" and t.id not in {x["id"] for x in topics}]}


def summaries(stack_id: str) -> list[dict]:
    cfg = load(stack_id)
    return [{k: t[k] for k in ("id", "label", "range", "title")} for t in cfg["tracks"]] if cfg else []
