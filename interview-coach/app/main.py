"""Interview Coach — scenario-based interview preparation for Java and Python, with an AI coach.

Run:  uvicorn app.main:app --port 8100    (or ./start.sh / start.cmd)
"""
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .api.routes import router
from .services.library import LibraryHolder


def create_app() -> FastAPI:
    app = FastAPI(title="Interview Coach", version="1.0")
    app.state.library = LibraryHolder()
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(config.STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
    return app


app = create_app()
