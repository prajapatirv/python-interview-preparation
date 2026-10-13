"""HTTP layer: thin handlers over services/. AI answers stream as plain UTF-8 text chunks."""
import json
import random
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from .. import config
from ..services import ai, auth, bank, checker, evaluation, insights, retrieve, submissions

router = APIRouter(prefix="/api")

MODES = {"ask", "explain", "interview", "improve", "generate", "jd"}


class AiRequest(BaseModel):
    mode: str
    stack: str
    topic: str = ""
    question_id: str = ""
    level: str = ""
    text: str = Field("", max_length=20000)      # free question, generate hint, or job description
    answer: str = Field("", max_length=12000)    # the candidate's answer


class SaveRequest(BaseModel):
    stack: str
    topic: str
    markdown: str = Field(..., max_length=30000)


def lib(request: Request):
    return request.app.state.library.lib


@router.get("/status")
def status(request: Request):
    return {"ai": ai.status(), "allow_save": config.ALLOW_SAVE,
            "auth": {"supabase_url": config.SUPABASE_URL, "anon_key": config.SUPABASE_ANON_KEY}
            if config.SUPABASE_URL else None,
            "stacks": [{"id": s["id"], "total": s["total"]} for s in lib(request).summary()]}


@router.get("/stacks")
def stacks(request: Request):
    return lib(request).summary()


@router.get("/topics/{stack}/{topic}")
def topic(stack: str, topic: str, request: Request):
    t = lib(request).topic(stack, topic)
    if t is None:
        raise HTTPException(404, "unknown topic")
    return lib(request).topic_detail(t)


@router.get("/search/{stack}")
def search(stack: str, request: Request, q: str = "", topic: str = "", level: str = "", k: int = 30):
    pool = lib(request).questions(stack, topic or None)
    if level:
        pool = [x for x in pool if x["level"] == level]
    hits = retrieve.search(pool, q, k=min(k, 100))
    return [{"score": s, **{f: x[f] for f in ("id", "title", "level", "kind", "topic", "source")}} for s, x in hits]


@router.get("/question/{qid}")
def question(qid: str, request: Request):
    q = lib(request).question(qid)
    if q is None:
        raise HTTPException(404, "unknown question")
    return q


@router.get("/round/{stack}")
def round_(stack: str, request: Request, topics: str = "", level: str = "", n: int = 5, kinds: str = "scenario,crib,guide"):
    """A mock-interview round: n random questions from the chosen topics (scenario questions first)."""
    wanted = {t for t in topics.split(",") if t}
    kind_set = {k for k in kinds.split(",") if k}
    pool = [q for q in lib(request).questions(stack) if (not wanted or q["topic"] in wanted)
            and (not level or q["level"] == level) and q["kind"] in kind_set]
    random.shuffle(pool)
    pool.sort(key=lambda q: q["kind"] != "scenario")
    return [{f: q[f] for f in ("id", "title", "level", "kind", "topic")} for q in pool[:max(1, min(n, 20))]]


@router.get("/doc")
def doc(path: str, request: Request):
    full = lib(request).allowed_doc(path)
    if full is None:
        raise HTTPException(404, "not a library document")
    return PlainTextResponse(full.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


@router.get("/coverage")
def coverage(request: Request):
    return lib(request).coverage()


@router.post("/ai")
async def ask_ai(req: AiRequest, request: Request):
    if req.mode not in MODES:
        raise HTTPException(400, f"mode must be one of {sorted(MODES)}")
    body = req.model_dump()
    try:
        ctx = ai.build_context(lib(request), body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if req.mode in ("explain",) and ctx["question"] is None:
        raise HTTPException(400, "explain needs a question_id")
    refs = [{"id": r["id"], "title": r["title"], "kind": r["kind"], "topic": r["topic"]} for r in ctx["refs"]]
    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "X-AI-Provider": ai.mode()}
    if refs:   # the UI shows which bank questions grounded the answer
        headers["X-AI-Refs"] = json.dumps(refs, ensure_ascii=True)
    if ctx.get("jd_topics"):
        headers["X-AI-Topics"] = json.dumps(ctx["jd_topics"], ensure_ascii=True)
    return StreamingResponse(ai.stream_answer(body, ctx), media_type="text/plain; charset=utf-8", headers=headers)


class CheckRequest(BaseModel):
    stack: str
    question_id: str = ""
    topic: str = ""
    level: str = ""
    text: str = Field("", max_length=2000)       # the question, when it is not from the bank
    answer: str = Field(..., min_length=1, max_length=12000)


class LabelRequest(BaseModel):
    label: str = Field("", max_length=80)


def store(request: Request):
    return request.app.state.store


class SubmitRequest(BaseModel):
    angle: str = Field("", max_length=80)        # "Spring Kafka angle", "start-up story", ...


class ReviewRequest(BaseModel):
    decision: str                                 # approve | reject
    note: str = Field("", max_length=500)
    angle: str = Field("", max_length=80)         # reviewer may retitle the angle on approval


def reviewer(user: auth.User = Depends(auth.current_user)) -> auth.User:
    if not user.is_reviewer:
        raise HTTPException(403, "reviewer role required")
    return user


@router.post("/check")
async def check_my_answer(req: CheckRequest, request: Request, user: auth.User = Depends(auth.current_user)):
    """Fact-check the learner's answer claim by claim; the attempt is stored and returned."""
    if not req.answer.strip():
        raise HTTPException(422, "answer is empty")
    try:
        result = await checker.check_answer(lib(request), req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))
    q = lib(request).question(req.question_id) if req.question_id else None
    return store(request).add_attempt(
        question_id=req.question_id or "free:" + req.text.strip()[:60], stack=req.stack,
        topic=q["topic"] if q else req.topic, level=req.level or (q["level"] if q else ""),
        answer_text=req.answer.strip(), check=result, provider=result["provider"],
        prompt_version=result["prompt_version"], user_id=user.id)


@router.get("/attempts")
def attempts(request: Request, question_id: str, saved_only: bool = False,
             user: auth.User = Depends(auth.current_user)):
    return store(request).attempts(question_id, saved_only=saved_only, user_id=user.id)


@router.post("/attempts/{attempt_id}/save")
def save_attempt(attempt_id: int, body: LabelRequest, request: Request,
                 user: auth.User = Depends(auth.current_user)):
    saved = store(request).save(attempt_id, body.label.strip(), user_id=user.id)
    if saved is None:
        raise HTTPException(404, "unknown attempt")
    return saved


@router.delete("/attempts/{attempt_id}")
def delete_attempt(attempt_id: int, request: Request, user: auth.User = Depends(auth.current_user)):
    if not store(request).delete(attempt_id, user_id=user.id):
        raise HTTPException(404, "unknown attempt")
    return {"deleted": attempt_id}


# ---------------------------------------------------------------- alternative answers (Phase C)

@router.post("/attempts/{attempt_id}/submit")
def submit_alternative(attempt_id: int, body: SubmitRequest, request: Request,
                       user: auth.User = Depends(auth.current_user)):
    """Propose a saved answer as another strong answer. The automatic gate decides if a reviewer sees it."""
    attempt = store(request).get_attempt(attempt_id, user_id=user.id)
    if attempt is None:
        raise HTTPException(404, "unknown attempt")
    q = lib(request).question(attempt["question_id"])
    if q is None or q["kind"] != "scenario":
        raise HTTPException(400, "alternatives can only be proposed for scenario questions in the bank")
    if not attempt["saved"]:
        raise HTTPException(400, "save the answer first")
    if any(s["attempt_id"] == attempt_id and s["status"] in ("pending", "approved", "promoted")
           for s in store(request).submissions(user_id=user.id)):
        raise HTTPException(409, "this answer was already submitted")
    verdict = submissions.gate(attempt)
    return store(request).add_submission(attempt=attempt, angle=body.angle.strip() or attempt["label"],
                                         status="pending" if verdict["passed"] else "rejected", gate=verdict)


@router.get("/submissions")
def my_submissions(request: Request, user: auth.User = Depends(auth.current_user)):
    return store(request).submissions(user_id=user.id)


@router.get("/review")
def review_queue(request: Request, status: str = "pending", user: auth.User = Depends(reviewer)):
    out = []
    for s in store(request).submissions(status or None):
        q = lib(request).question(s["question_id"])
        out.append({**s, "question_title": q["title"] if q else s["question_id"],
                    "reference": bank.section(q, "spoken") if q else ""})
    return out


@router.post("/review/{submission_id}")
def review(submission_id: int, body: ReviewRequest, request: Request, user: auth.User = Depends(reviewer)):
    sub = store(request).get_submission(submission_id)
    if sub is None:
        raise HTTPException(404, "unknown submission")
    if sub["status"] != "pending":
        raise HTTPException(409, f"submission is already {sub['status']}")
    if body.decision == "reject":
        return store(request).review_submission(submission_id, "rejected", note=body.note, reviewer_id=user.id)
    if body.decision != "approve":
        raise HTTPException(400, "decision must be approve or reject")
    try:
        path = lib(request).add_alternative(sub["question_id"], body.angle.strip() or sub["angle"], sub["answer_text"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    request.app.state.library.reload()
    return store(request).review_submission(submission_id, "promoted", note=body.note, reviewer_id=user.id,
                                            promoted_to=path)


# ---------------------------------------------------------------- is it improving? (Phase E)

@router.get("/insights")
def get_insights(request: Request, days: int = 90, user: auth.User = Depends(auth.current_user)):
    since = time.time() - max(1, min(days, 730)) * 86400
    # a reviewer sees everyone's evidence (that is what the curator learns from); a learner sees their own
    scope = None if user.is_reviewer else user.id
    st = store(request)
    titles = {q["id"]: q["title"] for s in lib(request).stacks for t in s.topics for q in t.questions}
    return insights.build(st.all_attempts(since, user_id=scope), st.submissions(user_id=scope), titles)


@router.get("/evals")
def eval_history(user: auth.User = Depends(reviewer)):
    return evaluation.history()


@router.post("/evals/run")
async def run_eval(request: Request, stack: str = "java", user: auth.User = Depends(reviewer)):
    summary = await evaluation.run(lib(request), stack, evaluation.load_cases())
    summary["passed"] = evaluation.passes(summary)
    evaluation.record(summary)
    return summary


@router.post("/questions/save")
def save_question(req: SaveRequest, request: Request):
    if not config.ALLOW_SAVE:
        raise HTTPException(403, "saving is disabled (COACH_ALLOW_SAVE=0)")
    _, _, qs = bank.parse_questions(req.markdown)
    if len(qs) != 1:
        raise HTTPException(422, "markdown must contain exactly one '### Q<n> [level] question' block")
    q = qs[0]
    if not q["sections"]:
        raise HTTPException(422, "the answer needs the **Section** labels of the scenario format")
    try:
        path = lib(request).save_question(req.stack, req.topic, q["level"] or "senior", q["title"], q["body"],
                                          q["tags"] + ["ai-draft"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    request.app.state.library.reload()
    return {"saved_to": path}


@router.post("/reload")
def reload(request: Request):
    new = request.app.state.library.reload()
    return {"stacks": [{"id": s["id"], "total": s["total"]} for s in new.summary()]}
