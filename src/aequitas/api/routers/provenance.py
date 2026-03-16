"""Provenance router — GET /api/provenance/{metric_id}."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aequitas.api.deps import get_db
from aequitas.api.models.responses import ProvenanceResponse
from aequitas.api.services.warehouse import query_provenance

router = APIRouter()


@router.get("/provenance/{metric_id}", response_model=ProvenanceResponse)
def get_provenance(metric_id: str) -> ProvenanceResponse:
    """Return provenance trail for a metric."""
    db = get_db()
    result = query_provenance(db, metric_id)
    if not result:
        raise HTTPException(404, f"No provenance for metric '{metric_id}'")
    return ProvenanceResponse(**result)
