"""HTTP layer: thin handlers over services/. AI answers stream as plain UTF-8 text chunks."""
import json
import random

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from .. import config
from ..services import ai, bank, retrieve

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
