"""Keyword retrieval over the question bank — enough for a few hundred questions, no vector DB.

Score = weighted term overlap (tags x3, title x2, answer body x1) scaled by inverse document
frequency, so "rebalancing" outranks "kafka" in a Kafka-heavy bank. Scenario answers get a small
boost over crib answers because they are the richer grounding for the model.
"""
import math
import re

STOP = set("""a an and are as at be but by can do does for from has have how i if in into is it its me my of on
or our so that the their them then there these they this to us was we were what when where which who why will
with would you your""".split())


def tokens(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9][a-z0-9.+#_-]*", text.lower()):
        w = w.strip(".-_")
        if len(w) < 2 or w in STOP:
            continue
        out.append(w)
        if w.endswith("ing") and len(w) > 5:          # rebalancing ~ rebalance, retrying ~ retry
            out.append(w[:-3])
        elif w.endswith("s") and len(w) > 3:
            out.append(w[:-1])
    return out


def _fields(q: dict) -> tuple[set, set, set]:
    tags = set()
    for t in q.get("tags", []):
        tags.update(tokens(t.replace("-", " ")))
        tags.add(t)
    return tags, set(tokens(q["title"])), set(tokens(q.get("body", "")))


def search(questions: list[dict], query: str, k: int = 5, level: str = "") -> list[tuple[float, dict]]:
    qt = set(tokens(query))
    if not qt or not questions:
        return []
    fields = [_fields(q) for q in questions]
    n = len(questions)
    df = {t: sum(1 for tg, ti, bo in fields if t in tg or t in ti or t in bo) for t in qt}
    scored = []
    for q, (tg, ti, bo) in zip(questions, fields):
        s = 0.0
        for t in qt:
            if not df[t]:
                continue
            idf = math.log(1 + n / df[t])
            s += idf * (3 * (t in tg) + 2 * (t in ti) + 1 * (t in bo))
        if s <= 0:
            continue
        if q.get("kind") == "scenario":
            s *= 1.25
        if level and q.get("level") == level:
            s *= 1.1
        scored.append((round(s, 3), q))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]
