"""PDF export router — GET /api/export/{dimension}."""
from __future__ import annotations

import re
from io import BytesIO

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from aequitas.api.deps import get_db
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


@router.get("/export/{dimension}")
async def export_dimension_pdf(
    dimension: str,
    region: str = Query("all"),
    urban_rural: str = Query("all"),
) -> StreamingResponse:
    """Generate a PDF report for a dimension + filter combination."""
    if dimension not in DIMENSION_PREFIXES:
        raise HTTPException(400, f"Unknown dimension: {dimension}")

    db = get_db()
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
