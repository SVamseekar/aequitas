"""Research briefing pack — CSV + printable HTML. Not a statutory BSIP submission."""

from __future__ import annotations

import csv
import html
import io
import json
from datetime import datetime, timezone
from typing import Any

from aequitas.analytics.reach import ITL1_NAMES
from aequitas.api.services.reach_query import query_bands, query_reach
from aequitas.api.services.score import score_for_filter

CAVEATS = [
    "Research pack, not a statutory BSIP submission.",
    "Not DfT guidance and not an official appraisal.",
    "Not TfL PTAL and not labelled official PTAL.",
    "Deprivation ranks and the quoteable score stay inside England.",
    "Hansen-style index is omitted unless origin–destination minutes exist.",
    "15/30/45 destination counts appear only when r5py has written them for that ITL1.",
]

IE_CAVEATS = [
    "Research pack for the Republic of Ireland. Not a statutory NTA, CSO, or Pobal submission.",
    "Not official NTA / TFI / Pobal HP guidance and not an official CAF/PAG appraisal.",
    "Not TfL PTAL and not labelled official PTAL.",
    "Deprivation ranks and the quoteable score stay inside the Republic (Pobal HP 2022).",
    "Hansen-style index is omitted unless origin–destination minutes exist.",
    "15/30/45 destination counts appear only when r5py has written them for this country.",
]

_IE_COUNTIES = {
    "dublin": "Dublin",
    "cork": "Cork",
    "galway": "Galway",
    "limerick": "Limerick",
    "waterford": "Waterford",
    "kerry": "Kerry",
    "clare": "Clare",
    "tipperary": "Tipperary",
    "kilkenny": "Kilkenny",
    "wexford": "Wexford",
    "wicklow": "Wicklow",
    "kildare": "Kildare",
    "meath": "Meath",
    "louth": "Louth",
    "westmeath": "Westmeath",
    "offaly": "Offaly",
    "laois": "Laois",
    "carlow": "Carlow",
    "longford": "Longford",
    "roscommon": "Roscommon",
    "mayo": "Mayo",
    "sligo": "Sligo",
    "leitrim": "Leitrim",
    "donegal": "Donegal",
    "cavan": "Cavan",
    "monaghan": "Monaghan",
}


def _place(region: str, urban_rural: str, country: str = "england") -> str:
    if country == "ireland":
        name = "Republic of Ireland" if region == "all" else _IE_COUNTIES.get(region, region.replace("-", " ").title())
    elif country == "netherlands":
        from aequitas.netherlands.constants import PROVINCE_NAME_BY_SLUG

        name = "Netherlands" if region == "all" else PROVINCE_NAME_BY_SLUG.get(region, region.replace("-", " ").title())
    else:
        name = ITL1_NAMES.get(region, "England") if region != "all" else "England"
    if urban_rural and urban_rural != "all":
        return f"{name} · {urban_rural}"
    return name


def pack_payload(
    db,
    *,
    region: str,
    urban_rural: str,
    dest_type: str = "jobs",
    cutoff: int = 45,
    studio_job: dict[str, Any] | None = None,
    country: str = "england",
) -> dict[str, Any]:
    key = (country or "england").strip().lower()
    score = score_for_filter(db, region, urban_rural).to_dict() if db is not None else {
        "score": None,
        "components": [],
        "n_areas": None,
        "note": "Warehouse not open.",
        "formula": "",
    }
    bands = query_bands(region, urban_rural, country=key)
    reach = query_reach(dest_type, cutoff, region, urban_rural, country=key)
    studio = None
    if studio_job:
        result = studio_job.get("result") or studio_job
        if isinstance(result, dict) and (result.get("score_before") is not None or result.get("people_gained") is not None):
            studio = {
                "job_id": studio_job.get("id"),
                "mode": result.get("mode"),
                "note": result.get("note"),
                "score_before": result.get("score_before"),
                "score_after": result.get("score_after"),
                "people_gained": result.get("people_gained"),
                "people_lost": result.get("people_lost"),
                "deciles": result.get("deciles") or [],
                "patch": result.get("patch"),
                "label": result.get("note") or "walk-to-stop change, not 45-minute jobs.",
            }
    if key == "ireland":
        vintages = {
            "network": "TFI GTFS_All.zip (Republic, pack vintage)",
            "census": "CSO Small Areas 2022",
            "hp": "Pobal HP Deprivation Index 2022 (ED join)",
            "centroids": "CSO SA 2022 centroids (Republic)",
            "reach": (
                "r5py destination counts"
                if reach.get("available")
                else "not computed for the Republic in this checkout"
            ),
        }
        caveats = IE_CAVEATS
        area_noun = "Small Areas"
        decile_noun = "HP"
    elif key == "netherlands":
        vintages = {
            "network": "OVapi gtfs-nl.zip (Netherlands, pack vintage)",
            "census": "CBS / PDOK buurt 2024",
            "ses_woa": "CBS SES-WOA 2023 (86092NED)",
            "centroids": "CBS Wijk- en Buurtkaart centroids",
            "reach": (
                "r5py destination counts"
                if reach.get("available")
                else "not computed for the Netherlands in this checkout"
            ),
        }
        caveats = [
            "Research pack for the Netherlands. Not a statutory CBS, PBL, or OV-wet submission.",
            "Not official concession guidance and not an official PBL appraisal.",
            "Deprivation ranks and the quoteable score stay inside the Netherlands (SES-WOA).",
            "15/30/45 destination counts appear only when r5py has written them for this country.",
        ]
        area_noun = "buurten"
        decile_noun = "SES-WOA"
    else:
        vintages = {
            "network": "BODS GTFS bulk (pack vintage)",
            "census": "Census 2021 LSOAs",
            "imd": "IMD 2025 ranks (in-country)",
            "centroids": "ONS LSOA Dec 2021 population-weighted centroids",
            "reach": (
                "r5py destination counts"
                if reach.get("available")
                else "not computed for this ITL1"
            ),
        }
        caveats = CAVEATS
        area_noun = "LSOAs"
        decile_noun = "IMD"
    return {
        "title": "Aequitas research briefing pack",
        "not_statutory_bsip": True,
        "place": _place(region, urban_rural, key),
        "filter": {"country": key, "region": region, "urban_rural": urban_rural},
        "area_noun": area_noun,
        "decile_noun": decile_noun,
        "vintages": vintages,
        "score": score,
        "bands": bands,
        "reach": reach,
        "studio": studio,
        "caveats": caveats,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }


def pack_csv(payload: dict[str, Any]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Section", "Item", "Value"])
    w.writerow(["Cover", "Title", payload["title"]])
    w.writerow(["Cover", "Place", payload["place"]])
    w.writerow(["Cover", "Country", payload["filter"]["country"]])
    w.writerow(["Cover", "Region", payload["filter"]["region"]])
    w.writerow(["Cover", "Urban or rural", payload["filter"]["urban_rural"]])
    for k, v in payload["vintages"].items():
        w.writerow(["Vintage", k, v])
    score = payload["score"]
    w.writerow(["Score", "In-country score", score.get("score")])
    w.writerow(["Score", "Areas", score.get("n_areas")])
    w.writerow(["Score", "Note", score.get("note")])
    for c in score.get("components") or []:
        w.writerow(["Score component", c.get("label") or c.get("id"), c.get("value")])
    bands = payload["bands"]
    w.writerow(["Bands", "Mode", bands.get("mode")])
    w.writerow(["Bands", "People", bands.get("people")])
    area_noun = payload.get("area_noun") or "LSOAs"
    decile_noun = payload.get("decile_noun") or "IMD"
    w.writerow(["Bands", area_noun, bands.get("n_areas")])
    w.writerow(["Bands", "Share in worst two bands (%)", bands.get("pct_worst_two")])
    w.writerow(["Bands", "400 m coverage share", bands.get("coverage_400m_share")])
    w.writerow(["Bands", "Formula", bands.get("formula")])
    w.writerow(["Bands", "Map aggregation", bands.get("map_aggregation")])
    w.writerow(["Bands", "Unmatched note", bands.get("unmatched_note")])
    for row in bands.get("people_by_band_decile") or []:
        decile = row.get("imd_decile") if "imd_decile" in row else row.get("hp_decile")
        w.writerow(
            [
                f"People by band and {decile_noun} decile",
                f"Band {row['band']} · decile {decile}",
                row["people"],
            ]
        )
    reach = payload["reach"]
    w.writerow(["Reach", "Available", reach.get("available")])
    w.writerow(["Reach", "Destination type", reach.get("dest_type")])
    w.writerow(["Reach", "Cutoff (minutes)", reach.get("cutoff")])
    w.writerow(["Reach", "Median destinations", reach.get("median")])
    w.writerow(["Reach", "Note", reach.get("note")])
    studio = payload.get("studio")
    if studio:
        w.writerow(["Studio", "Job", studio.get("job_id")])
        w.writerow(["Studio", "Mode", studio.get("mode")])
        w.writerow(["Studio", "Score before", studio.get("score_before")])
        w.writerow(["Studio", "Score after", studio.get("score_after")])
        w.writerow(["Studio", "People gained", studio.get("people_gained")])
        w.writerow(["Studio", "People lost", studio.get("people_lost")])
        w.writerow(["Studio", "Label", studio.get("label")])
        if studio.get("patch"):
            w.writerow(["Studio", "Patch JSON", json.dumps(studio["patch"])])
        for d in studio.get("deciles") or []:
            decile = d.get("imd_decile") if d.get("imd_decile") is not None else d.get("hp_decile")
            w.writerow(
                [
                    "Studio decile",
                    f"{decile_noun} decile {decile}",
                    f"gained {d.get('people_gained')}; lost {d.get('people_lost')}",
                ]
            )
    for c in payload["caveats"]:
        w.writerow(["Caveat", "Research note", c])
    return buf.getvalue()


def pack_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape("" if x is None else str(x))

    score = payload["score"]
    bands = payload["bands"]
    reach = payload["reach"]
    studio = payload.get("studio")
    area_noun = payload.get("area_noun") or "LSOAs"
    decile_noun = payload.get("decile_noun") or "IMD"
    rows = "".join(
        f"<tr><td>{esc(r['band'])}</td>"
        f"<td>{esc(r.get('imd_decile', r.get('hp_decile')))}</td>"
        f"<td>{esc(f'{r['people']:,}')}</td><td>{esc(r['n_areas'])}</td></tr>"
        for r in (bands.get("people_by_band_decile") or [])
    )
    caveats = "".join(f"<li>{esc(c)}</li>" for c in payload["caveats"])
    comps = "".join(
        f"<tr><td>{esc(c.get('label'))}</td><td>{esc(c.get('value'))}</td></tr>"
        for c in (score.get("components") or [])
    )
    studio_html = ""
    if studio:
        studio_html = f"""
        <h2>Studio before / after</h2>
        <p>{esc(studio.get('label'))}</p>
        <p>Score {esc(studio.get('score_before'))} → {esc(studio.get('score_after'))}.
        People gained {esc(studio.get('people_gained'))}; lost {esc(studio.get('people_lost'))}.</p>
        """
    reach_html = (
        f"<p>Median {esc(reach.get('dest_type'))} in {esc(reach.get('cutoff'))} minutes: "
        f"{esc(reach.get('median'))} ({esc(reach.get('n_areas'))} {esc(area_noun)}).</p>"
        if reach.get("available")
        else f"<p>{esc(reach.get('note') or f'15/30/45 not precomputed for this {area_noun} pack.')}</p>"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{esc(payload['title'])} — {esc(payload['place'])}</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 2rem auto; max-width: 48rem; color: #141311; }}
    h1 {{ font-size: 1.6rem; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ccc; padding: 0.35rem 0.5rem; text-align: left; }}
    .muted {{ color: #555; font-size: 0.9rem; }}
    @media print {{ body {{ margin: 1rem; }} }}
  </style>
</head>
<body>
  <h1>{esc(payload['title'])}</h1>
  <p class="muted">{esc(payload['place'])} · research pack, not a statutory submission.</p>
  <h2>Vintages</h2>
  <ul>
    {''.join(f'<li>{esc(k)}: {esc(v)}</li>' for k, v in payload['vintages'].items())}
  </ul>
  <h2>In-country score</h2>
  <p><strong>{esc(score.get('score'))}</strong> — {esc(score.get('note'))}</p>
  <table><thead><tr><th>Component</th><th>Value</th></tr></thead><tbody>{comps}</tbody></table>
  <h2>Access / service bands</h2>
  <p>{esc(bands.get('narrative'))}</p>
  <p class="muted">{esc(bands.get('formula'))}</p>
  <p class="muted">{esc(bands.get('map_aggregation'))}</p>
  <p class="muted">{esc(bands.get('unmatched_note'))}</p>
  <table>
    <thead><tr><th>Band</th><th>{esc(decile_noun)} decile</th><th>People</th><th>{esc(area_noun)}</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <h2>15 / 30 / 45</h2>
  {reach_html}
  {studio_html}
  <h2>Caveats</h2>
  <ul>{caveats}</ul>
</body>
</html>
"""
