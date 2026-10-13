"""App factory: registers routers and global exception handlers.
Run: uvicorn app.main:app --reload   (from the 05_web_apis_fastapi folder)"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.repositories import NotFoundError
from app.routers import orders
from app.services import ValidationError

app = FastAPI(title="Order Service", version="1.0.0")

app.include_router(orders.router)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"error": str(exc)})


@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"error": str(exc)})


@app.get("/health")
async def health():
    return {"status": "ok"}
