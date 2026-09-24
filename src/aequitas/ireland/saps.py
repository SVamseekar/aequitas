"""Join free CSO SAPS 2022 Small Area columns (unemployment, no-car, 65+)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

_ELDERLY = (
    "T1_1AGE65_69T",
    "T1_1AGE70_74T",
    "T1_1AGE75_79T",
    "T1_1AGE80_84T",
    "T1_1AGEGE_85T",
)
# Census 2022 Theme 2 ethnic/cultural background, usually resident, total.
# Counts stay null when GUID does not match — never filled with 0.
_ETHNIC = (
    ("T2_2WI", "eth_white_irish"),
    ("T2_2WIT", "eth_traveller"),
    ("T2_2OW", "eth_other_white"),
    ("T2_2BBI", "eth_black"),
    ("T2_2AAI", "eth_asian"),
    ("T2_2OTH", "eth_other"),
)
# Census 2022 Theme 8: unemployed split into short-term (ST) and long-term (LTU).
# T15_1_NC / T15_1_TC = households with no car / all households.


def default_saps_path(project_root: Path) -> Path:
    return project_root / "data" / "raw" / "ireland" / "saps_2022.csv"


def attach_saps_theme_shares(areas: pd.DataFrame, saps_path: Path) -> pd.DataFrame:
    """Add unemployment, no-car, 65+, and Theme 2 ethnic counts from SAPS if the file exists."""
    out = areas.copy()
    if not saps_path.exists():
        logger.warning("SAPS not on disk at {} — d2/d3/d4/f3 stay omitted", saps_path)
        return out
    want = [
        "GUID",
        "SA_GUID_2022",
        "T1_1AGETT",
        "T8_1_ST",
        "T8_1_LTUT",
        "T8_1_TT",
        "T15_1_NC",
        "T15_1_TC",
        *_ELDERLY,
        *[src for src, _dst in _ETHNIC],
        "T2_2T",
    ]
    try:
        sap = pd.read_csv(saps_path, usecols=lambda c: str(c) in want or str(c).lower() in {"guid", "sa_guid_2022"})
    except Exception as exc:  # noqa: BLE001
        logger.warning("SAPS theme parse failed: {}", exc)
        return out
    cols = {c.lower(): c for c in sap.columns}
    code = cols.get("guid") or cols.get("sa_guid_2022")
    if code is None:
        return out
    pop = cols.get("t1_1agett")
    st = cols.get("t8_1_st")
    ltu = cols.get("t8_1_ltut")
    tot8 = cols.get("t8_1_tt")
    nc = cols.get("t15_1_nc")
    tc = cols.get("t15_1_tc")
    age_cols = [cols[k.lower()] for k in _ELDERLY if k.lower() in cols]
    sap = sap.copy()
    sap["sa_code"] = sap[code].astype(str)
    if st is not None and ltu is not None and tot8 is not None:
        denom = pd.to_numeric(sap[tot8], errors="coerce")
        num = pd.to_numeric(sap[st], errors="coerce").fillna(0) + pd.to_numeric(sap[ltu], errors="coerce").fillna(0)
        sap["unemp_rate"] = (num / denom.where(denom > 0)).clip(0, 1)
    if nc is not None and tc is not None:
        denom = pd.to_numeric(sap[tc], errors="coerce")
        sap["no_car_share"] = (pd.to_numeric(sap[nc], errors="coerce") / denom.where(denom > 0)).clip(0, 1)
    if pop is not None and age_cols:
        elder = sum(pd.to_numeric(sap[c], errors="coerce").fillna(0) for c in age_cols)
        denom = pd.to_numeric(sap[pop], errors="coerce")
        sap["elderly_share"] = (elder / denom.where(denom > 0)).clip(0, 1)
    for src, dst in _ETHNIC:
        orig = cols.get(src.lower())
        if orig is not None:
            sap[dst] = pd.to_numeric(sap[orig], errors="coerce")
    total = cols.get("t2_2t")
    if total is not None:
        sap["eth_total"] = pd.to_numeric(sap[total], errors="coerce")
    theme_cols = ("unemp_rate", "no_car_share", "elderly_share", "eth_total", *[dst for _src, dst in _ETHNIC])
    keep = ["sa_code"] + [c for c in theme_cols if c in sap.columns]
    if len(keep) == 1:
        return out
    drop = [c for c in theme_cols if c in out.columns]
    if drop:
        out = out.drop(columns=drop)
    merged = out.merge(sap[keep].drop_duplicates("sa_code"), on="sa_code", how="left")
    for col in ("unemp_rate", "no_car_share", "elderly_share", "eth_total"):
        if col in merged:
            logger.info("SAPS {} non-null {:.1%}", col, float(merged[col].notna().mean()))
    return merged
