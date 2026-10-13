"""HTTP layer: thin handlers that delegate to app.services (no business logic here)."""
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from .. import config
from ..services import ai, docs
from ..services.catalog import Catalog, Example, read_source
from ..services.runner import run_example
from .schemas import AiBody, RunBody

router = APIRouter(prefix="/api")

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _catalog(request: Request) -> Catalog:
    return request.app.state.catalog


def _example(request: Request, example_id: str) -> Example:
    ex = _catalog(request).get(example_id)
    if not ex:
        raise HTTPException(404, f"unknown example {example_id}")
    return ex


def _sse(events):
    async def body():
        async for ev in events:
            yield f"data: {json.dumps(ev)}\n\n"
    return StreamingResponse(body(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/catalog")
def catalog(request: Request):
    cat = _catalog(request)
    return {"topics": cat.topics, "root": str(config.PREP_ROOT), "error": cat.error,
            "features": {"edit": config.ALLOW_EDIT, "ai": ai.available(),
                         "ai_mode": ai.mode(), "timeout": config.RUN_TIMEOUT_S,
                         "python": config.PYTHON_VERSION}}


@router.post("/reload")
def reload_catalog(request: Request):
    return {"examples": _catalog(request).reload()}


@router.get("/source")
def source(request: Request, id: str):
    return {"id": id, "source": read_source(_example(request, id))}


@router.get("/docs/{doc_id}")
def deep_dive(doc_id: str):
    text = docs.read_doc(config.PREP_ROOT, doc_id)
    if text is None:
        raise HTTPException(404, f"unknown document {doc_id}")
    return {"id": doc_id, "markdown": text}


@router.post("/run")
async def run(request: Request, body: RunBody):
    ex = _example(request, body.id)
    if body.code is not None:
        if not config.ALLOW_EDIT:
            raise HTTPException(403, "editing disabled; start with PREP_ALLOW_EDIT=1")
        if ex.is_suite:
            raise HTTPException(400, "a test suite cannot be run from edited code")
    return _sse(run_example(ex, body.code))


@router.post("/ai")
async def ai_endpoint(request: Request, body: AiBody):
    ex = _example(request, body.id)
    src = body.code if (body.code and config.ALLOW_EDIT) else read_source(ex)

    async def events():
        async for chunk in ai.stream_answer(body.mode, src, body.output, body.question):
            yield {"text": chunk}
        yield {"done": True}
    return _sse(events())
