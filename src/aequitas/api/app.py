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

    # Health — verifies DuckDB connectivity
    @app.get("/api/health")
    def health() -> dict:
        from aequitas.api.deps import get_db
        generator = get_db()
        db = next(generator)
        if db is None:
            return {"status": "degraded", "warehouse": "not found"}
        try:
            db.execute("SELECT 1").fetchone()
            return {"status": "ok", "warehouse": "connected"}
        except Exception as exc:
            from loguru import logger
            logger.exception(f"Health check database error: {exc}")
            return {"status": "degraded", "warehouse": "unavailable"}
        finally:
            generator.close()

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
