"""In-country AllTransit-style quoteable score (0–100).

One formula for home, ticker, and compare. Terms are 0–1 and clipped.
Missing terms are dropped and remaining weights renormalised.

    score = 100 × (
        0.40 × pop_within_400m_share
      + 0.25 × evening_served_share
      + 0.20 × weekday_frequency_norm
      + 0.15 × (1 − deprivation_service_gap_norm)
    )

Never reuse a national term when the filter lacks that component.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCORE_WEIGHTS: dict[str, float] = {
    "pop_within_400m": 0.40,
    "evening_served": 0.25,
    "weekday_frequency": 0.20,
    "deprivation_service": 0.15,
}

SCORE_LABELS: dict[str, str] = {
    "pop_within_400m": "Share of people within 400 m of a stop",
    "evening_served": "Share of areas with an evening bus",
    "weekday_frequency": "Weekday service quality (0–100, scaled)",
    "deprivation_service": "Deprivation–service gap (inverted)",
}

SCORE_FORMULA = (
    "100 × (0.40 × pop_within_400m_share + 0.25 × evening_served_share "
    "+ 0.20 × weekday_frequency_norm + 0.15 × (1 − deprivation_service_gap_norm)); "
    "missing terms dropped and remaining weights renormalised"
)


def clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True)
class ScoreComponent:
    id: str
    label: str
    design_weight: float
    weight_used: float
    value: float | None
    missing: bool


@dataclass(frozen=True)
class ScoreResult:
    score: float | None
    components: list[ScoreComponent]
    dropped: list[str]
    n_areas: int | None
    note: str | None
    formula: str = SCORE_FORMULA
    filter: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": None if self.score is None else round(self.score, 1),
            "components": [
                {
                    "id": c.id,
                    "label": c.label,
                    "design_weight": c.design_weight,
                    "weight_used": c.weight_used,
                    "value": None if c.value is None else round(c.value, 4),
                    "missing": c.missing,
                }
                for c in self.components
            ],
            "dropped": list(self.dropped),
            "n_areas": self.n_areas,
            "note": self.note,
            "formula": self.formula,
            "filter": dict(self.filter),
        }


def compute_score(
    terms: dict[str, float | None],
    *,
    n_areas: int | None = None,
    region: str = "all",
    urban_rural: str = "all",
) -> ScoreResult:
    """Compute the quoteable score from 0–1 terms (None = missing)."""
    present: list[tuple[str, float, float]] = []
    dropped: list[str] = []
    for key, design_w in SCORE_WEIGHTS.items():
        raw = terms.get(key)
        if raw is None:
            dropped.append(key)
            continue
        present.append((key, design_w, clip01(raw)))

    if not present:
        components = [
            ScoreComponent(
                id=k,
                label=SCORE_LABELS[k],
                design_weight=w,
                weight_used=0.0,
                value=None,
                missing=True,
            )
            for k, w in SCORE_WEIGHTS.items()
        ]
        note = "No score for this filter — required inputs are missing."
        if region == "E12000007" and urban_rural == "rural":
            note = "London has no rural LSOAs — no in-country score for this cut."
        return ScoreResult(
            score=None,
            components=components,
            dropped=list(SCORE_WEIGHTS),
            n_areas=n_areas or 0,
            note=note,
            filter={"region": region, "urban_rural": urban_rural},
        )

    weight_sum = sum(w for _, w, _ in present)
    components: list[ScoreComponent] = []
    weighted = 0.0
    present_ids = {k for k, _, _ in present}
    for key, design_w in SCORE_WEIGHTS.items():
        if key not in present_ids:
            components.append(
                ScoreComponent(
                    id=key,
                    label=SCORE_LABELS[key],
                    design_weight=design_w,
                    weight_used=0.0,
                    value=None,
                    missing=True,
                )
            )
            continue
        value = next(v for k, _, v in present if k == key)
        used = design_w / weight_sum
        weighted += used * value
        components.append(
            ScoreComponent(
                id=key,
                label=SCORE_LABELS[key],
                design_weight=design_w,
                weight_used=used,
                value=value,
                missing=False,
            )
        )

    note = None
    if dropped:
        labels = ", ".join(SCORE_LABELS[k].split(" (")[0].lower() for k in dropped)
        note = f"{labels} not in this cut — weights renormalised."

    return ScoreResult(
        score=100.0 * weighted,
        components=components,
        dropped=dropped,
        n_areas=n_areas,
        note=note,
        filter={"region": region, "urban_rural": urban_rural},
    )


def terms_from_section_stats(
    a3: dict[str, Any] | None,
    b2: dict[str, Any] | None,
    b1: dict[str, Any] | None,
    d1: dict[str, Any] | None,
) -> tuple[dict[str, float | None], int | None]:
    """Map warehouse section stats onto score terms. Missing stats stay None."""
    terms: dict[str, float | None] = {
        "pop_within_400m": None,
        "evening_served": None,
        "weekday_frequency": None,
        "deprivation_service": None,
    }
    n_areas: int | None = None

    if a3 and not a3.get("insufficient_data"):
        pct = a3.get("pct_covered")
        if isinstance(pct, (int, float)):
            terms["pop_within_400m"] = float(pct) / 100.0
        if isinstance(a3.get("n_lsoas"), int):
            n_areas = int(a3["n_lsoas"])
        elif isinstance(a3.get("n_sas"), int):
            n_areas = int(a3["n_sas"])

    if b2 and not b2.get("insufficient_data"):
        isolated = b2.get("pct_evening_isolated")
        if isinstance(isolated, (int, float)):
            terms["evening_served"] = 1.0 - float(isolated) / 100.0

    if b1 and not b1.get("insufficient_data"):
        # Regional rows store the filter SQI in `value`; `national_avg` is
        # England-wide and must not be reused on a regional cut.
        avg = b1.get("value")
        if not isinstance(avg, (int, float)):
            avg = b1.get("national_avg")
        if isinstance(avg, (int, float)):
            terms["weekday_frequency"] = float(avg) / 100.0

    if d1 and not d1.get("insufficient_data"):
        r = d1.get("r")
        if isinstance(r, (int, float)):
            # |r| of coverage vs deprivation is the gap; invert so higher is better.
            terms["deprivation_service"] = 1.0 - clip01(abs(float(r)))

    return terms, n_areas
