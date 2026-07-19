"""Provenance router — GET /api/provenance/{metric_id}."""
from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from aequitas.api.deps import get_db
from aequitas.api.models.responses import ProvenanceResponse
from aequitas.api.services.warehouse import PROVENANCE_ID_ALIASES, query_provenance

router = APIRouter(tags=["provenance"])


@router.get("/provenance/{metric_id}", response_model=ProvenanceResponse)
def get_provenance(
    metric_id: str,
    db: duckdb.DuckDBPyConnection | None = Depends(get_db),
) -> ProvenanceResponse:
    """Return provenance trail for a metric.

    Accepts warehouse IDs (``gini_national``) and public aliases (``gini``,
    ``f1_gini``, ``palma``, …). Unknown IDs return 404 with a clear message.
    """
    if db is None:
        raise HTTPException(404, f"No provenance for metric '{metric_id}'")

    result = query_provenance(db, metric_id)
    if not result:
        known = sorted(set(PROVENANCE_ID_ALIASES) | set(PROVENANCE_ID_ALIASES.values()))
        raise HTTPException(
            404,
            f"No provenance for metric '{metric_id}'. "
            f"Known keys include: {', '.join(known[:12])}…",
        )
    return ProvenanceResponse(**result)
