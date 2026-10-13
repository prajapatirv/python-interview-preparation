"""Interview Coach — scenario-based interview preparation for Java and Python, with an AI coach.

Run:  uvicorn app.main:app --port 8100    (or ./start.sh / start.cmd)
"""
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .api.routes import router
from .services.library import LibraryHolder
from .services.store import SqliteStore


def make_store():
    """Supabase when configured (multi-user), otherwise local single-user SQLite."""
    if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
        from .services.supabase_store import SupabaseStore
        return SupabaseStore(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    return SqliteStore(config.DATA_DIR / "coach.db")


def create_app() -> FastAPI:
    app = FastAPI(title="Interview Coach", version="1.0")
    app.state.library = LibraryHolder()
    app.state.store = make_store()
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(config.STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
    return app


app = create_app()
