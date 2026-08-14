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
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    # Required by authlib OAuth (stores state in request.session)
    from starlette.middleware.sessions import SessionMiddleware

    app.add_middleware(
        SessionMiddleware,
        secret_key=cfg.session_secret or "dev-insecure-secret-change-me",
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

    @app.get("/api/packs")
    def packs() -> dict:
        from pathlib import Path

        from aequitas.api.deps import _state

        ie = _state.get("ie_db_path")
        nl = _state.get("nl_db_path")
        en = _state.get("db_path")
        regions: list[dict] = []
        nl_regions: list[dict] = []
        if ie is not None:
            import duckdb

            conn = duckdb.connect(str(ie), read_only=True)
            try:
                row = conn.execute(
                    "SELECT value FROM metadata WHERE key = 'regions_json'"
                ).fetchone()
                if row:
                    import json

                    regions = json.loads(row[0])
            except Exception:
                regions = []
            finally:
                conn.close()
        from aequitas.warehouse.packs import list_packs

        if nl is not None:
            import duckdb

            conn = duckdb.connect(str(nl), read_only=True)
            try:
                row = conn.execute(
                    "SELECT value FROM metadata WHERE key = 'regions_json'"
                ).fetchone()
                if row:
                    import json

                    nl_regions = json.loads(row[0])
            except Exception:
                nl_regions = []
            finally:
                conn.close()
        dated = {
            "england": list_packs("england"),
            "ireland": list_packs("ireland"),
            "netherlands": list_packs("netherlands"),
        }
        return {
            "england": {
                "packReady": Path(en).exists() if en else False,
                "regions": None,
                "dates": dated["england"],
            },
            "ireland": {
                "packReady": Path(ie).exists() if ie else False,
                "regions": regions or None,
                "dates": dated["ireland"],
            },
            "netherlands": {
                "packReady": Path(nl).exists() if nl else False,
                "regions": nl_regions or None,
                "dates": dated["netherlands"],
            },
            "france": {"packReady": False, "regions": None},
        }

    # Register routers
    from aequitas.api.routers import (
        auth as auth_router,
        chat,
        conversations,
        export,
        lsoa,
        metrics,
        map_data,
        overview,
        policy_notes,
        profiles,
        provenance,
        reach,
        saved_analyses,
        saved_regions,
        score,
        sections,
        studio,
        time_series,
    )

    app.include_router(overview.router, prefix="/api")
    app.include_router(score.router, prefix="/api")
    app.include_router(time_series.router, prefix="/api")
    app.include_router(map_data.router, prefix="/api")
    app.include_router(reach.router, prefix="/api")
    app.include_router(studio.router, prefix="/api")
    app.include_router(sections.router, prefix="/api")
    app.include_router(lsoa.router, prefix="/api")
    app.include_router(provenance.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")
    app.include_router(metrics.router, prefix="/api")
    app.include_router(export.router, prefix="/api")
    app.include_router(auth_router.router, prefix="/api")
    app.include_router(saved_analyses.router, prefix="/api")
    app.include_router(policy_notes.router, prefix="/api")
    app.include_router(saved_regions.router, prefix="/api")
    app.include_router(profiles.router, prefix="/api")

    return app


# Module-level app for `uvicorn aequitas.api.app:app` (see AGENTS.md / README).
app = create_app()
