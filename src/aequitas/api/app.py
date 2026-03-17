"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aequitas.api.config import ApiConfig
from aequitas.api.deps import lifespan


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    cfg = ApiConfig()
    app = FastAPI(
        title="Aequitas API",
        description="UK bus transport policy intelligence",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Health
    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    # Register routers
    from aequitas.api.routers import overview, sections, lsoa, provenance, chat, conversations, metrics, export
    app.include_router(overview.router, prefix="/api")
    app.include_router(sections.router, prefix="/api")
    app.include_router(lsoa.router, prefix="/api")
    app.include_router(provenance.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")
    app.include_router(metrics.router, prefix="/api")
    app.include_router(export.router, prefix="/api")

    return app
