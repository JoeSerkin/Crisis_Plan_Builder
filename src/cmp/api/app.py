"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from cmp.api.routes.engagements import router as engagements_router
from cmp.api.routes.knowledge import router as knowledge_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Crisis Management Planner API",
        version="2.0.0",
        description="Consultant workflow API for discovery, planning, and deliverables.",
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "2.0.0"}

    app.include_router(engagements_router, prefix="/api/v1")
    app.include_router(knowledge_router, prefix="/api/v1")

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def ui() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    return app
