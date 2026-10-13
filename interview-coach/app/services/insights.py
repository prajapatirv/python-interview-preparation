"""Is the coach working? Aggregates stored attempts and submissions into the dashboard numbers
(docs/SELF_IMPROVING_DESIGN.md section 7, "Measuring that it is actually improving"). Pure functions over
the rows a ``Store`` returns, so they work for SQLite and Supabase alike."""
import time
from collections import Counter, defaultdict

WEEK = 7 * 86400
WRONG = ("incorrect", "outdated")


def _avg(xs):
    return round(sum(xs) / len(xs), 2) if xs else None


def _wrong_rate(attempts: list[dict]) -> float | None:
    claims = [c for a in attempts for c in a["check"].get("claims", [])]
    return round(sum(c["verdict"] in WRONG for c in claims) / len(claims), 3) if claims else None


def build(attempts: list[dict], submissions: list[dict], titles: dict[str, str] | None = None,
          now: float | None = None) -> dict:
    now = now or time.time()
    titles = titles or {}
    by_topic = defaultdict(list)
    by_question = defaultdict(list)
    weekly = defaultdict(list)
    for a in attempts:
        by_topic[a["topic"] or "(free question)"].append(a)
        by_question[a["question_id"]].append(a)
        weekly[int((now - a["created_at"]) // WEEK)].append(a["total_score"])
    topics = []
    for topic, rows in by_topic.items():
        recent = [a["total_score"] for a in rows if now - a["created_at"] < WEEK]
        before = [a["total_score"] for a in rows if now - a["created_at"] >= WEEK]
        topics.append({"topic": topic, "attempts": len(rows), "avg_score": _avg([a["total_score"] for a in rows]),
                       "wrong_claim_rate": _wrong_rate(rows),
                       "trend": round(_avg(recent) - _avg(before), 2) if recent and before else None})
    topics.sort(key=lambda t: (t["avg_score"] is None, t["avg_score"]))
    weak = [{"question_id": qid, "title": titles.get(qid, qid), "attempts": len(rows),
             "avg_score": _avg([a["total_score"] for a in rows]), "wrong_claim_rate": _wrong_rate(rows)}
            for qid, rows in by_question.items() if len(rows) >= 2]
    weak.sort(key=lambda w: w["avg_score"])
    wrong = Counter()
    for a in attempts:
        for c in a["check"].get("claims", []):
            if c["verdict"] in WRONG:
                wrong[(a["question_id"], c["text"].strip().lower())] += 1
    misconceptions = [{"question_id": q, "title": titles.get(q, q), "claim": text, "count": n,
                       "correction": next((c["correction"] for a in by_question[q] for c in a["check"]["claims"]
                                           if c["text"].strip().lower() == text and c["correction"]), "")}
                      for (q, text), n in wrong.most_common(10)]
    reviewed = [s for s in submissions if s["status"] in ("approved", "promoted", "rejected")
                and s.get("reviewer_id")]
    accepted = sum(s["status"] in ("approved", "promoted") for s in reviewed)
    return {
        "attempts": len(attempts), "avg_score": _avg([a["total_score"] for a in attempts]),
        "wrong_claim_rate": _wrong_rate(attempts),
        "by_provider": dict(Counter(a["provider"] for a in attempts)),
        "by_topic": topics, "weakest_questions": weak[:10], "misconceptions": misconceptions,
        "weekly": [{"weeks_ago": w, "attempts": len(v), "avg_score": _avg(v)} for w, v in sorted(weekly.items())],
        "submissions": {"by_status": dict(Counter(s["status"] for s in submissions)),
                        "acceptance_rate": round(accepted / len(reviewed), 2) if reviewed else None},
    }
