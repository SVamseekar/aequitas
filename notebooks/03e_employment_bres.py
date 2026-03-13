# %% [markdown]
# # 03e — NOMIS BRES Employment Audit
#
# **Purpose:** Audit MSOA-level employment data and create a population-weighted LSOA-level proxy.
# Employment centres are critical inputs for job accessibility analysis in Series 04.
#
# **Input:** `data/raw/nomis/bres_msoa_2023.csv` (BRES 2023, England MSOAs)
# **Output:** `data/audit/lsoa_employment_proxy.parquet`
#
# **Mapping strategy:** LSOA→MSOA lookup fetched from ONS Open Geography Portal (OA21/LSOA21/MSOA21
# lookup service). Each MSOA's employment total is distributed to constituent LSOAs proportional
# to each LSOA's share of the MSOA's total population (from master_lsoa_table).
#
# **Validation standard:** PASS / WARN / FAIL consistent with 01_data_audit.

# %%
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from loguru import logger

# %%
ROOT = Path("/Users/souravamseekarmarti/Projects/aequitas")
DATA = ROOT / "data"
FIGURES = DATA / "audit"

# Cache path for the ONS LSOA→MSOA lookup (avoids re-fetching on re-runs)
LOOKUP_CACHE = DATA / "audit/lsoa_msoa_lookup_cache.parquet"

logger.info("03e — NOMIS BRES Employment Audit")
print("03e — NOMIS BRES Employment Audit")
print("=" * 50)

# %% [markdown]
# ## Section 1 — Load and profile BRES MSOA data

# %%
bres_path = DATA / "raw/nomis/bres_msoa_2023.csv"
bres_raw = pd.read_csv(bres_path)

logger.info(f"Loaded BRES CSV: {bres_raw.shape[0]} rows × {bres_raw.shape[1]} cols")
print(f"Raw shape:   {bres_raw.shape}")
print(f"Columns:     {bres_raw.columns.tolist()}")
print(f"Dtypes:\n{bres_raw.dtypes}")
print(f"\nNull counts:\n{bres_raw.isnull().sum()}")
print(f"\nSample rows:")
print(bres_raw.head(5).to_string())

# %% [markdown]
# ## Section 2 — Validate and filter to England MSOAs

# %%
# Filter to England MSOAs (E02xxxxxxx)
bres_eng = bres_raw[bres_raw["GEOGRAPHY_CODE"].str.startswith("E02")].copy()

checks = []

# GT-018: England MSOA count
eng_msoa_count = len(bres_eng)
status = "PASS" if eng_msoa_count == 6791 else ("WARN" if eng_msoa_count >= 6700 else "FAIL")
checks.append(("GT-018", status, f"England MSOAs = {eng_msoa_count} (expect 6,791)"))
logger.info(f"GT-018: England MSOAs = {eng_msoa_count}")

# Null check
null_count = bres_eng["OBS_VALUE"].isnull().sum()
status = "PASS" if null_count == 0 else "FAIL"
checks.append(("NULL-01", status, f"OBS_VALUE nulls = {null_count} (expect 0)"))
logger.info(f"NULL-01: OBS_VALUE nulls = {null_count}")

# OBS_VALUE range
obs_min = int(bres_eng["OBS_VALUE"].min())
obs_max = int(bres_eng["OBS_VALUE"].max())
obs_mean = bres_eng["OBS_VALUE"].mean()
total_employees = int(bres_eng["OBS_VALUE"].sum())
checks.append(("RANGE-01", "INFO", f"OBS_VALUE range: {obs_min:,} – {obs_max:,}, mean={obs_mean:,.0f}"))

# GT-019: Total employees
status = "PASS" if 25_000_000 <= total_employees <= 30_000_000 else "WARN"
checks.append(("GT-019", status, f"Total England employees = {total_employees:,} (expect ~27.3M)"))
logger.info(f"GT-019: Total England employees = {total_employees:,}")

for chk_id, status, msg in checks:
    print(f"[{status:4s}] {chk_id}: {msg}")

print(f"\nEngland MSOAs: {eng_msoa_count:,}")
print(f"Total employees: {total_employees:,}")

# %% [markdown]
# ## Section 3 — MSOA employment distribution

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Histogram of employment per MSOA
axes[0].hist(bres_eng["OBS_VALUE"], bins=60, color="#2563eb", edgecolor="white", alpha=0.85)
axes[0].set_xlabel("Employees per MSOA")
axes[0].set_ylabel("Count")
axes[0].set_title("Distribution of Employment per MSOA\n(BRES 2023, England)")
axes[0].axvline(obs_mean, color="red", linestyle="--", linewidth=1.5, label=f"Mean: {obs_mean:,.0f}")
axes[0].legend()

# Top 20 MSOAs
top20 = bres_eng.nlargest(20, "OBS_VALUE")[["GEOGRAPHY_NAME", "OBS_VALUE"]]
axes[1].barh(top20["GEOGRAPHY_NAME"][::-1], top20["OBS_VALUE"][::-1], color="#16a34a")
axes[1].set_xlabel("Employees")
axes[1].set_title("Top 20 MSOAs by Employment\n(BRES 2023)")
axes[1].tick_params(axis="y", labelsize=7)

plt.tight_layout()
fig_path = FIGURES / "fig_03e_msoa_employment_distribution.png"
plt.savefig(fig_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {fig_path}")

# Employment by region (derive from MSOA name prefix is not reliable — use GEOGRAPHY_CODE prefix)
# E02000001–E02001325 = London, but codes are not regionally sequential — skip region breakdown
# Instead show bottom 20
bottom20 = bres_eng.nsmallest(20, "OBS_VALUE")[["GEOGRAPHY_NAME", "OBS_VALUE"]]
print("\nTop 5 MSOAs by employment:")
print(top20.head().to_string(index=False))
print("\nBottom 5 MSOAs by employment:")
print(bottom20.head().to_string(index=False))

# %% [markdown]
# ## Section 4 — LSOA→MSOA lookup via ONS Open Geography Portal
#
# **Method:** Download OA21/LSOA21/MSOA21 lookup from ONS ArcGIS REST service
# (`OA21_LAD22_LSOA21_MSOA21_LEP22_EN_LU_V2`). Deduplicate to unique LSOA21CD→MSOA21CD pairs.
# This is the authoritative ONS 2021 geographic hierarchy.
#
# **Cache:** Result is written to `data/audit/lsoa_msoa_lookup_cache.parquet` on first run.
# Subsequent runs load from cache, skipping the API entirely.

# %%
SERVICE_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "OA21_LAD22_LSOA21_MSOA21_LEP22_EN_LU_V2/FeatureServer/0/query"
)
PAGE_SIZE = 1000
MAX_RETRIES = 3


def fetch_lsoa_msoa_lookup() -> pd.DataFrame:
    """Download LSOA21→MSOA21 lookup from ONS Open Geography Portal.

    Paginates through all 178,605 OA records and deduplicates to unique LSOA→MSOA pairs.
    Each page fetch is retried up to MAX_RETRIES times with exponential backoff on network
    errors. Returns a DataFrame with columns LSOA21CD, MSOA21CD.

    Raises:
        RuntimeError: If a page fetch fails after all retries.
    """
    records = []
    offset = 0
    total_fetched = 0

    logger.info("Fetching ONS LSOA21→MSOA21 lookup (paginated)...")
    print("Fetching ONS LSOA21→MSOA21 lookup (paginated)...")
    while True:
        params = (
            f"?where=1%3D1"
            f"&outFields=LSOA21CD%2CMSOA21CD"
            f"&returnGeometry=false"
            f"&f=json"
            f"&resultRecordCount={PAGE_SIZE}"
            f"&resultOffset={offset}"
        )
        url = SERVICE_URL + params

        # Retry with exponential backoff on transient network errors
        for attempt in range(MAX_RETRIES):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "aequitas-eda/1.0"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read())
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(
                        f"ONS API failed after {MAX_RETRIES} attempts at offset {offset}"
                    ) from exc
                wait = 2 ** attempt
                logger.warning(
                    f"ONS API error at offset {offset}, attempt {attempt + 1}/{MAX_RETRIES} "
                    f"— retrying in {wait}s: {exc}"
                )
                time.sleep(wait)

        features = data.get("features", [])
        if not features:
            break

        for feat in features:
            a = feat["attributes"]
            records.append((a["LSOA21CD"], a["MSOA21CD"]))

        total_fetched += len(features)
        exceeded = data.get("exceededTransferLimit", False)

        if total_fetched % 20000 == 0 or not exceeded:
            logger.info(f"Fetched {total_fetched:,} OA records...")
            print(f"  Fetched {total_fetched:,} OA records...")

        if not exceeded or len(features) < PAGE_SIZE:
            break

        offset += PAGE_SIZE
        time.sleep(0.05)  # polite rate limiting

    logger.info(f"Total OA records downloaded: {total_fetched:,}")
    print(f"Total OA records downloaded: {total_fetched:,}")
    df = pd.DataFrame(records, columns=["LSOA21CD", "MSOA21CD"])
    # Deduplicate to unique LSOA→MSOA pairs (each LSOA maps to exactly 1 MSOA)
    df = df.drop_duplicates(subset="LSOA21CD").reset_index(drop=True)
    logger.info(f"Unique LSOA→MSOA pairs: {len(df):,}")
    print(f"Unique LSOA→MSOA pairs: {len(df):,}")
    return df


# Load from cache if available, otherwise fetch from ONS API and cache result
if LOOKUP_CACHE.exists():
    logger.info(f"Loading LSOA→MSOA lookup from cache: {LOOKUP_CACHE}")
    print(f"Loading from cache: {LOOKUP_CACHE}")
    lsoa_msoa_lookup = pd.read_parquet(LOOKUP_CACHE)
    logger.info(f"Cache loaded: {len(lsoa_msoa_lookup):,} rows")
    print(f"Cache loaded: {len(lsoa_msoa_lookup):,} rows")
else:
    lsoa_msoa_lookup = fetch_lsoa_msoa_lookup()
    lsoa_msoa_lookup.to_parquet(LOOKUP_CACHE, index=False)
    logger.info(f"Lookup cached to: {LOOKUP_CACHE}")
    print(f"Cached to: {LOOKUP_CACHE}")

print(f"\nLookup sample:")
print(lsoa_msoa_lookup.head(5).to_string(index=False))

# %% [markdown]
# ## Section 4b — Validate the lookup

# %%
lookup_checks = []

# Filter to England LSOAs only (E01xxxxxxx)
lsoa_msoa_eng = lsoa_msoa_lookup[lsoa_msoa_lookup["LSOA21CD"].str.startswith("E01")].copy()
eng_lsoa_in_lookup = len(lsoa_msoa_eng)

# Expect 33,755 England LSOAs
status = "PASS" if eng_lsoa_in_lookup == 33755 else ("WARN" if eng_lsoa_in_lookup >= 33000 else "FAIL")
lookup_checks.append(("LOOKUP-01", status, f"England LSOAs in lookup = {eng_lsoa_in_lookup:,} (expect 33,755)"))
logger.info(f"LOOKUP-01: England LSOAs in lookup = {eng_lsoa_in_lookup:,}")

# Each LSOA maps to exactly one MSOA — check no duplicates remain
dup_count = lsoa_msoa_eng.duplicated(subset="LSOA21CD").sum()
status = "PASS" if dup_count == 0 else "FAIL"
lookup_checks.append(("LOOKUP-02", status, f"Duplicate LSOA entries = {dup_count} (expect 0)"))
logger.info(f"LOOKUP-02: Duplicate LSOA entries = {dup_count}")

# MSOAs in lookup should match BRES MSOAs
msoa_in_lookup = set(lsoa_msoa_eng["MSOA21CD"].unique())
msoa_in_bres = set(bres_eng["GEOGRAPHY_CODE"].unique())
msoa_overlap = len(msoa_in_lookup & msoa_in_bres)
msoa_only_in_bres = msoa_in_bres - msoa_in_lookup
status = "PASS" if msoa_overlap >= 6700 else "WARN"
lookup_checks.append(("LOOKUP-03", status, f"MSOAs in both lookup and BRES = {msoa_overlap:,} (expect ~6,791)"))
logger.info(f"LOOKUP-03: MSOAs in both lookup and BRES = {msoa_overlap:,}; only-in-BRES = {len(msoa_only_in_bres)}")

for chk_id, status, msg in lookup_checks:
    print(f"[{status:4s}] {chk_id}: {msg}")

# %% [markdown]
# ## Section 4c — Diagnose MSOAs present in BRES but absent from ONS lookup (LOOKUP-04)
#
# LOOKUP-03 may report MSOAs in BRES that have no match in the ONS OA→LSOA→MSOA lookup.
# This cell identifies them by name and employment volume to determine whether the gap
# is negligible (expected for boundary edge cases) or material.

# %%
print(f"\nMSOAs in BRES but NOT in ONS lookup ({len(msoa_only_in_bres)}):")
missing_df = bres_eng[bres_eng["GEOGRAPHY_CODE"].isin(msoa_only_in_bres)][
    ["GEOGRAPHY_CODE", "GEOGRAPHY_NAME", "OBS_VALUE"]
].sort_values("OBS_VALUE", ascending=False)
print(missing_df.to_string())

missing_emp = missing_df["OBS_VALUE"].sum()
missing_pct = missing_emp / total_employees * 100
status = "PASS" if missing_pct < 0.5 else "WARN"
lookup_checks.append(("LOOKUP-04", status,
    f"Employment in unmatched MSOAs = {missing_emp:,} ({missing_pct:.2f}% of total"
    f" — below 0.5% threshold is acceptable)"))
logger.info(
    f"LOOKUP-04: {len(msoa_only_in_bres)} unmatched MSOAs, "
    f"{missing_emp:,} employees ({missing_pct:.2f}% of total) — {status}"
)
print(f"\n[{status:4s}] LOOKUP-04: Employment in unmatched MSOAs = {missing_emp:,} ({missing_pct:.2f}% of total)")

# %% [markdown]
# ## Section 5 — Load master LSOA table and create population-weighted proxy
#
# **Approach (Option B — population weighted):**
# For each MSOA, distribute its BRES employment total to constituent LSOAs proportional to
# each LSOA's share of the MSOA's total population.
#
# Formula: `employment_proxy[lsoa] = msoa_employment × (lsoa_pop / msoa_total_pop)`

# %%
master = pd.read_parquet(DATA / "audit/master_lsoa_table.parquet")
logger.info(f"Master LSOA table loaded: {master.shape[0]} rows × {master.shape[1]} cols")
print(f"Master LSOA table: {master.shape}")
print(f"Population column: 'population' — {master['population'].describe().to_dict()}")

# Merge MSOA code into master via lookup
master_with_msoa = master[["lsoa_cd", "lsoa_nm", "lad_cd", "lad_nm", "population",
                            "imd_score", "imd_decile"]].copy()
master_with_msoa = master_with_msoa.merge(
    lsoa_msoa_eng[["LSOA21CD", "MSOA21CD"]],
    left_on="lsoa_cd",
    right_on="LSOA21CD",
    how="left"
).drop(columns="LSOA21CD")
master_with_msoa = master_with_msoa.rename(columns={"MSOA21CD": "msoa_cd"})

msoa_unmatched = master_with_msoa["msoa_cd"].isnull().sum()
logger.info(f"LSOAs without MSOA code after merge: {msoa_unmatched}")
print(f"\nLSOAs without MSOA code: {msoa_unmatched}")

# Merge BRES employment totals
bres_for_merge = bres_eng[["GEOGRAPHY_CODE", "OBS_VALUE"]].rename(
    columns={"GEOGRAPHY_CODE": "msoa_cd", "OBS_VALUE": "msoa_employment"}
)
master_with_msoa = master_with_msoa.merge(bres_for_merge, on="msoa_cd", how="left")

employment_unmatched = master_with_msoa["msoa_employment"].isnull().sum()
logger.info(f"LSOAs without BRES employment match: {employment_unmatched}")
print(f"LSOAs without BRES employment match: {employment_unmatched}")

# Cast msoa_employment to nullable Int64 — left join introduces NaN which coerces to float64
master_with_msoa["msoa_employment"] = pd.array(
    master_with_msoa["msoa_employment"], dtype=pd.Int64Dtype()
)

# %%
# Compute MSOA total population for weighting
msoa_pop_totals = (
    master_with_msoa.groupby("msoa_cd")["population"]
    .sum()
    .rename("msoa_total_pop")
    .reset_index()
)
master_with_msoa = master_with_msoa.merge(msoa_pop_totals, on="msoa_cd", how="left")

# Population weight for each LSOA within its MSOA
master_with_msoa["pop_weight"] = np.where(
    master_with_msoa["msoa_total_pop"] > 0,
    master_with_msoa["population"] / master_with_msoa["msoa_total_pop"],
    np.nan
)

# Apply weight to get LSOA employment proxy (float64 intentional — fractional values expected)
master_with_msoa["employment_proxy"] = (
    master_with_msoa["msoa_employment"].astype("float64") * master_with_msoa["pop_weight"]
)

logger.info(f"employment_proxy computed: {master_with_msoa['employment_proxy'].notna().sum():,} non-null LSOAs")
print("\nemployment_proxy summary:")
print(master_with_msoa["employment_proxy"].describe())

# %% [markdown]
# ## Section 6 — Validate proxy sums back to MSOA totals

# %%
# Sum proxy employment back to MSOA level and compare with original BRES
proxy_by_msoa = (
    master_with_msoa.dropna(subset=["employment_proxy"])
    .groupby("msoa_cd")["employment_proxy"]
    .sum()
    .rename("proxy_sum")
    .reset_index()
)
validation_df = proxy_by_msoa.merge(bres_for_merge, on="msoa_cd", how="inner")
validation_df["diff_pct"] = (
    (validation_df["proxy_sum"] - validation_df["msoa_employment"].astype("float64")).abs()
    / validation_df["msoa_employment"].astype("float64")
) * 100

max_diff = validation_df["diff_pct"].max()
mean_diff = validation_df["diff_pct"].mean()
perfect_match = (validation_df["diff_pct"] < 0.01).sum()

print(f"MSOAs validated: {len(validation_df):,}")
print(f"Max proxy error vs MSOA total: {max_diff:.4f}%")
print(f"Mean proxy error: {mean_diff:.6f}%")
print(f"MSOAs with <0.01% error: {perfect_match:,} / {len(validation_df):,}")

proxy_checks = []
status = "PASS" if max_diff < 1.0 else ("WARN" if max_diff < 5.0 else "FAIL")
proxy_checks.append(("PROXY-01", status,
                      f"Max MSOA proxy sum error = {max_diff:.4f}% (expect <1%)"))
logger.info(f"PROXY-01: Max MSOA proxy sum error = {max_diff:.4f}% — {status}")

lsoa_coverage = master_with_msoa["employment_proxy"].notna().sum()
coverage_pct = lsoa_coverage / len(master_with_msoa) * 100
status = "PASS" if coverage_pct >= 95.0 else ("WARN" if coverage_pct >= 85.0 else "FAIL")
proxy_checks.append(("PROXY-02", status,
                      f"LSOAs with employment proxy = {lsoa_coverage:,} / {len(master_with_msoa):,} "
                      f"({coverage_pct:.1f}%) — expect ≥95%"))
logger.info(f"PROXY-02: LSOA coverage = {lsoa_coverage:,} ({coverage_pct:.1f}%) — {status}")

for chk_id, status, msg in proxy_checks:
    print(f"[{status:4s}] {chk_id}: {msg}")

# %% [markdown]
# ## Section 7 — Cross-reference with IMD: employment deserts vs deprivation

# %%
# Employment desert = bottom quintile of employment proxy
proxy_valid = master_with_msoa.dropna(subset=["employment_proxy", "imd_score"]).copy()
emp_q20 = proxy_valid["employment_proxy"].quantile(0.20)

proxy_valid["employment_desert"] = proxy_valid["employment_proxy"] <= emp_q20
proxy_valid["high_deprivation"] = proxy_valid["imd_decile"] <= 2  # most deprived 20%

# Cross-tabulation
cross_tab = pd.crosstab(
    proxy_valid["high_deprivation"].map({True: "High deprivation (decile 1-2)", False: "Lower deprivation"}),
    proxy_valid["employment_desert"].map({True: "Employment desert", False: "Employment OK"}),
    margins=True
)
print("Employment desert × High deprivation cross-tab:")
print(cross_tab)

triple_jeopardy = proxy_valid[proxy_valid["employment_desert"] & proxy_valid["high_deprivation"]]
logger.info(f"Triple jeopardy LSOAs (employment desert + high deprivation): {len(triple_jeopardy):,}")
print(f"\nLSOAs in employment desert AND high deprivation: {len(triple_jeopardy):,}")

# Correlation: employment proxy vs IMD score
corr = proxy_valid[["employment_proxy", "imd_score"]].corr().iloc[0, 1]
logger.info(f"Pearson correlation (employment_proxy vs imd_score): {corr:.4f}")
print(f"\nPearson correlation (employment_proxy vs imd_score): {corr:.4f}")

# Scatter plot
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

sample = proxy_valid.sample(min(5000, len(proxy_valid)), random_state=42)
axes[0].scatter(sample["imd_score"], sample["employment_proxy"],
                alpha=0.3, s=5, color="#7c3aed")
axes[0].set_xlabel("IMD Score (higher = more deprived)")
axes[0].set_ylabel("Employment Proxy (LSOA)")
axes[0].set_title(f"Employment vs Deprivation\n(Pearson r = {corr:.3f})")

# Employment proxy by IMD decile (box)
decile_data = [
    proxy_valid[proxy_valid["imd_decile"] == d]["employment_proxy"].dropna().values
    for d in range(1, 11)
]
axes[1].boxplot(decile_data, labels=range(1, 11), showfliers=False)
axes[1].set_xlabel("IMD Decile (1=most deprived, 10=least deprived)")
axes[1].set_ylabel("Employment Proxy")
axes[1].set_title("Employment Proxy Distribution by IMD Decile")

plt.tight_layout()
fig_path2 = FIGURES / "fig_03e_employment_imd_correlation.png"
plt.savefig(fig_path2, dpi=150, bbox_inches="tight")
plt.close()
print(f"\nSaved: {fig_path2}")

# %% [markdown]
# ## Section 8 — Save output

# %%
output_cols = [
    "lsoa_cd", "lsoa_nm", "lad_cd", "lad_nm",
    "msoa_cd", "msoa_employment", "population", "msoa_total_pop",
    "pop_weight", "employment_proxy"
]
out_df = master_with_msoa[output_cols].copy()
out_path = DATA / "audit/lsoa_employment_proxy.parquet"
out_df.to_parquet(out_path, index=False)
logger.info(f"Saved output: {out_path} ({len(out_df):,} rows)")
print(f"Saved: {out_path}")
print(f"Rows: {len(out_df):,}")
print(f"Columns: {out_df.columns.tolist()}")
print(f"\nSchema preview:")
print(out_df.dtypes)
print(f"\nSample output:")
print(out_df[out_df["employment_proxy"].notna()].head(5).to_string())

# %% [markdown]
# ## Section 9 — Validation summary

# %%
all_checks = checks + lookup_checks + proxy_checks

print("\n" + "=" * 60)
print("03e — VALIDATION SUMMARY")
print("=" * 60)

pass_count = sum(1 for _, s, _ in all_checks if s == "PASS")
warn_count = sum(1 for _, s, _ in all_checks if s == "WARN")
fail_count = sum(1 for _, s, _ in all_checks if s == "FAIL")
info_count = sum(1 for _, s, _ in all_checks if s == "INFO")

for chk_id, status, msg in all_checks:
    print(f"  [{status:4s}] {chk_id}: {msg}")

print(f"\nTotal: {pass_count} PASS | {warn_count} WARN | {fail_count} FAIL | {info_count} INFO")

if fail_count > 0:
    print("\nCRITICAL: FAILs require investigation before downstream use.")
elif warn_count > 0:
    print("\nWARNs: Review before using in production pipeline.")
else:
    print("\nAll checks PASS. Output ready for Series 04.")

print("\n--- Key figures for figures-registry.md ---")
print(f"GT-018: England MSOAs (BRES 2023) = {eng_msoa_count:,}")
print(f"GT-019: Total England employees (BRES 2023) = {total_employees:,}")
print(f"Mapping: Population-weighted MSOA→LSOA proxy via ONS OA21/LSOA21/MSOA21 lookup")
print(f"LSOA coverage: {lsoa_coverage:,} / 33,755 ({coverage_pct:.1f}%)")
print(f"Employment desert + high deprivation (triple jeopardy): {len(triple_jeopardy):,} LSOAs")
print(f"Employment–IMD Pearson correlation: {corr:.4f}")
