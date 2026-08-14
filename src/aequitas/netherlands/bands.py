"""Netherlands service bands — same assign_service_band, buurt fields."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from aequitas.analytics.bands import assign_service_band
from aequitas.core.config import PipelineConfig


def write_netherlands_bands(cfg: PipelineConfig | None = None) -> Path | None:
    cfg = cfg or PipelineConfig()
    table = cfg.processed_dir / "netherlands" / "buurt_table.parquet"
    if not table.exists():
        logger.info("Netherlands buurt table missing — no bands")
        return None
    df = pd.read_parquet(table)
    rows = []
    for row in df.itertuples(index=False):
        band, why = assign_service_band(
            stop_count=getattr(row, "stop_count", 0),
            no_service=getattr(row, "no_service", False),
            evening_isolated=getattr(row, "evening_isolated", False),
            sunday_desert=getattr(row, "sunday_desert", False),
            sqi=getattr(row, "sqi", None),
        )
        rows.append(
            {
                "lsoa": str(row.buurt_code),
                "region": str(row.region),
                "region_code": str(row.region),
                "urban_rural": str(getattr(row, "urban_rural", "all")),
                "population": float(row.population),
                "imd_decile": int(getattr(row, "ses_decile", 0) or 0),
                "stop_count": int(getattr(row, "stop_count", 0) or 0),
                "band": band,
                "band_reason": why,
                "scheme": "service",
            }
        )
    out = pd.DataFrame(rows)
    dest = cfg.processed_dir / "netherlands" / "buurt_access_bands.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(dest, index=False)
    logger.info("Netherlands service bands: {} buurten → {}", len(out), dest)
    return dest
