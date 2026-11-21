"""PDF export router — GET /api/export/{dimension}."""
from __future__ import annotations

import re
from io import BytesIO
from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from aequitas.api.auth.dependencies import require_session
from aequitas.api.deps import country_warehouse, get_db
from aequitas.api.services.reach_scope import current_reach_scope
from aequitas.api.services.warehouse import DIMENSION_PREFIXES, query_sections

router = APIRouter(tags=["export"])

_PAGE_W, _PAGE_H = A4


def _build_pdf(dimension: str, sections: list[dict], region: str, urban_rural: str) -> bytes:
    """Render a ReportLab PDF and return raw bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Cover heading
    story.append(Paragraph(f"Aequitas — {dimension.replace('_', ' ').title()}", styles["h1"]))
    story.append(Paragraph(f"Region: {region} | Area type: {urban_rural}", styles["Normal"]))
    story.append(Paragraph("NOT OFFICIAL DfT GUIDANCE — Policy analysis tool only", styles["Italic"]))
    story.append(Spacer(1, 0.5 * cm))

    for sec in sections:
        sec_id = sec.get("section_id", "")
        title = sec_id.replace("_", " ").title()
        narrative = sec.get("narrative", "")
        stats = sec.get("stats", {})

        story.append(Paragraph(title, styles["h2"]))

        # Stats table
        if stats:
            data = [["Metric", "Value"]]
            for k, v in stats.items():
                if isinstance(v, (int, float)):
                    data.append([k.replace("_", " ").title(), str(round(v, 4))])
                elif isinstance(v, str):
                    data.append([k.replace("_", " ").title(), v])

            if len(data) > 1:
                tbl = Table(data, colWidths=[8 * cm, 8 * cm])
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), (0.2, 0.2, 0.5)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), (1, 1, 1)),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [(0.95, 0.95, 0.98), (1, 1, 1)]),
                    ("GRID", (0, 0), (-1, -1), 0.25, (0.7, 0.7, 0.7)),
                ]))
                story.append(tbl)
                story.append(Spacer(1, 0.3 * cm))

        if narrative:
            story.append(Paragraph(narrative[:2000], styles["Normal"]))

        story.append(Spacer(1, 0.5 * cm))

    doc.build(story)
    return buf.getvalue()


def _pack_country_or_404(country: str) -> str:
    key = (country or "england").strip().lower()
    if key == "netherlands":
        raise HTTPException(
            status_code=404,
            detail="The Netherlands research pack is not built yet.",
        )
    if key not in {"england", "ireland", "france"}:
        raise HTTPException(status_code=404, detail=f"Unknown country {key!r}.")
    return key


@router.get("/export/pack.json", dependencies=[Depends(current_reach_scope)])
def review_research_pack(
    db: Annotated[duckdb.DuckDBPyConnection | None, Depends(country_warehouse)],
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    dest_type: str = Query("jobs", pattern="^(jobs|gp|school)$"),
    cutoff: int = Query(45),
    country: str = Query("england"),
) -> dict:
    from aequitas.api.services.export_pack import pack_payload

    return pack_payload(db, region=region, urban_rural=urban_rural,
                        dest_type=dest_type, cutoff=cutoff, country=_pack_country_or_404(country))


@router.get("/export/pack.csv", dependencies=[Depends(current_reach_scope)])
def export_research_pack_csv(
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    dest_type: str = Query("jobs"),
    cutoff: int = Query(45),
    studio_job: str | None = Query(None),
    country: str = Query("england"),
    db: duckdb.DuckDBPyConnection | None = Depends(country_warehouse),
) -> StreamingResponse:
    from aequitas.api.routers import studio as studio_router
    from aequitas.api.services.export_pack import pack_csv, pack_payload

    key = _pack_country_or_404(country)
    job = None
    if studio_job:
        with studio_router._LOCK:
            job = studio_router._JOBS.get(studio_job)
    payload = pack_payload(
        db,
        region=region,
        urban_rural=urban_rural,
        dest_type=dest_type,
        cutoff=cutoff,
        studio_job=job,
        country=key,
    )
    body = pack_csv(payload)
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", f"aequitas_research_pack_{region}_{urban_rural}")
    return StreamingResponse(
        iter([body.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe}.csv"'},
    )


@router.get("/export/pack.html", dependencies=[Depends(current_reach_scope)])
def export_research_pack_html(
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    dest_type: str = Query("jobs"),
    cutoff: int = Query(45),
    studio_job: str | None = Query(None),
    country: str = Query("england"),
    db: duckdb.DuckDBPyConnection | None = Depends(country_warehouse),
) -> StreamingResponse:
    from aequitas.api.routers import studio as studio_router
    from aequitas.api.services.export_pack import pack_html, pack_payload

    key = _pack_country_or_404(country)
    job = None
    if studio_job:
        with studio_router._LOCK:
            job = studio_router._JOBS.get(studio_job)
    payload = pack_payload(
        db,
        region=region,
        urban_rural=urban_rural,
        dest_type=dest_type,
        cutoff=cutoff,
        studio_job=job,
        country=key,
    )
    body = pack_html(payload)
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", f"aequitas_research_pack_{region}_{urban_rural}")
    return StreamingResponse(
        iter([body.encode("utf-8")]),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'inline; filename="{safe}.html"'},
    )


@router.get("/export/{dimension}")
async def export_dimension_pdf(
    dimension: str,
    region: str = Query("all"),
    urban_rural: str = Query("all"),
    db: duckdb.DuckDBPyConnection | None = Depends(get_db),
    session: dict = Depends(require_session),
    country: str = Query("england"),
    pack: str | None = Query(None),
    as_of: str | None = Query(None),
    mode: str = Query("bus"),
) -> StreamingResponse:
    """Generate a PDF report for a dimension + filter combination."""
    if country not in {"england", "ireland", "netherlands", "france"}:
        raise HTTPException(404, "Unknown country. No PDF country fallback is available.")
    if country != "england" or mode != "bus":
        raise HTTPException(400, "Dimension PDF exports support the current England bus network only.")
    current_reach_scope(country=country, pack=pack, as_of=as_of)
    if dimension not in DIMENSION_PREFIXES:
        raise HTTPException(400, f"Unknown dimension: {dimension}")
    sections: list[dict] = []
    if db is not None:
        rows = query_sections(db, dimension, region, urban_rural)
        sections = rows

    pdf_bytes = _build_pdf(dimension, sections, region, urban_rural)
    # Sanitize filename — strip anything not alphanumeric, underscore, or hyphen
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", f"aequitas_{dimension}_{region}_{urban_rural}")
    filename = f"{safe}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
