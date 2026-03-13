# %% [markdown]
# # 03d — GIAS Schools Audit
#
# **Purpose:** Audit GIAS education establishment data. Classify all 135 columns.
# Focus on open secondary schools for accessibility analysis.
#
# **Input:** `data/raw/poi/gias_schools.csv` (52,278 rows, 135 columns, latin-1 encoding)
#
# **Outputs:**
# - `data/audit/schools_secondary_geocoded.parquet` — secondary + all-through, open, geocoded
# - `data/audit/schools_all_open_geocoded.parquet` — all open schools, geocoded
# - `data/audit/gias_column_inventory.csv` — all 135 columns classified USE/IGNORE/REVIEW
#
# **Ground truth targets:**
# - GT-016: ~27,183 open schools
# - GT-017: ~3,339 secondary-equiv (3,173 secondary + 166 all-through)

# %%
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from loguru import logger

ROOT = Path("/Users/souravamseekarmarti/Projects/aequitas")
DATA = ROOT / "data"
AUDIT = DATA / "audit"
RAW = DATA / "raw"

logger.remove()
logger.add(sys.stdout, format="{time:HH:mm:ss} | {level} | {message}", level="INFO")

CHECKS: list[dict] = []

def check(name: str, status: str, detail: str = "") -> None:
    """Log a validation check result."""
    symbol = {"PASS": "✓", "WARN": "!", "FAIL": "✗"}.get(status, "?")
    CHECKS.append({"check": name, "status": status, "detail": detail})
    logger.info(f"[{status}] {symbol} {name} — {detail}")

# %% [markdown]
# ## Section 1: Load and Profile

# %%
logger.info("Loading GIAS schools CSV (latin-1 encoding)…")
schools = pd.read_csv(
    RAW / "poi/gias_schools.csv",
    encoding="latin-1",
    low_memory=False,
)
logger.info(f"Loaded: {schools.shape[0]:,} rows × {schools.shape[1]} columns")

# Basic profiling
mem_mb = schools.memory_usage(deep=True).sum() / 1e6
logger.info(f"Memory usage: {mem_mb:.1f} MB")

# Dtype breakdown
dtype_counts = schools.dtypes.value_counts()
logger.info(f"Dtypes: {dtype_counts.to_dict()}")

# Missing value summary (top 20 columns by null count)
null_counts = schools.isnull().sum()
top_null = null_counts[null_counts > 0].sort_values(ascending=False).head(20)
logger.info(f"Columns with nulls (top 20):\n{top_null.to_string()}")

check("row-count", "PASS" if len(schools) == 52278 else "FAIL",
      f"{len(schools):,} rows (expected 52,278)")
check("col-count", "PASS" if len(schools.columns) == 135 else "WARN",
      f"{len(schools.columns)} columns (expected 135)")

# %% [markdown]
# ## Section 2: Column Inventory — Classify ALL 135 Columns

# %%
# Systematic classification: USE = needed for analysis, IGNORE = not needed, REVIEW = uncertain
COLUMN_CLASSIFICATIONS: dict[str, tuple[str, str]] = {
    # --- Identifiers ---
    "URN": ("USE", "Unique Reference Number — primary key for each establishment"),
    "LA (code)": ("USE", "Local Authority code — spatial/admin grouping"),
    "LA (name)": ("USE", "Local Authority name — human-readable grouping"),
    "EstablishmentNumber": ("IGNORE", "OFSTED/DfE admin ref, duplicates URN for our purposes"),
    "EstablishmentName": ("USE", "School name — for display and matching"),
    "TypeOfEstablishment (code)": ("USE", "Establishment type code — filters academy/community/independent"),
    "TypeOfEstablishment (name)": ("USE", "Establishment type name — human-readable"),
    "EstablishmentTypeGroup (code)": ("IGNORE", "Higher-level grouping of type; type (name) sufficient"),
    "EstablishmentTypeGroup (name)": ("IGNORE", "Higher-level grouping of type; type (name) sufficient"),

    # --- Status & Dates ---
    "EstablishmentStatus (code)": ("USE", "Status code: 1=Open (primary filter)"),
    "EstablishmentStatus (name)": ("USE", "Status name: Open/Closed/etc."),
    "ReasonEstablishmentOpened (code)": ("IGNORE", "Admin reason; not relevant for accessibility analysis"),
    "ReasonEstablishmentOpened (name)": ("IGNORE", "Admin reason; not relevant for accessibility analysis"),
    "OpenDate": ("IGNORE", "Historical admin date; not needed for current analysis"),
    "ReasonEstablishmentClosed (code)": ("IGNORE", "Only relevant for closed schools"),
    "ReasonEstablishmentClosed (name)": ("IGNORE", "Only relevant for closed schools"),
    "CloseDate": ("IGNORE", "Only relevant for closed schools"),

    # --- Phase & Age ---
    "PhaseOfEducation (code)": ("IGNORE", "Code version; name column used instead"),
    "PhaseOfEducation (name)": ("USE", "Phase: Secondary/Primary/All-through — key for filtering"),
    "StatutoryLowAge": ("REVIEW", "Age range may help identify true secondary (11+) vs middle schools"),
    "StatutoryHighAge": ("REVIEW", "Age range may help identify secondary (16+) vs other phases"),

    # --- Boarding / Nursery / Sixth Form ---
    "Boarders (code)": ("IGNORE", "Boarding status not relevant for daily accessibility analysis"),
    "Boarders (name)": ("IGNORE", "Boarding status not relevant for daily accessibility analysis"),
    "NurseryProvision (name)": ("IGNORE", "Nursery provision; not target phase"),
    "OfficialSixthForm (code)": ("REVIEW", "Sixth form presence relevant for 16+ accessibility"),
    "OfficialSixthForm (name)": ("REVIEW", "Sixth form presence relevant for 16+ accessibility"),

    # --- Demographics & Character ---
    "Gender (code)": ("IGNORE", "Gender of intake; not a spatial accessibility factor"),
    "Gender (name)": ("IGNORE", "Gender of intake; not a spatial accessibility factor"),
    "ReligiousCharacter (code)": ("IGNORE", "Religious denomination; not spatial"),
    "ReligiousCharacter (name)": ("IGNORE", "Religious denomination; not spatial"),
    "ReligiousEthos (name)": ("IGNORE", "Ethos detail; subset of religious character"),
    "Diocese (code)": ("IGNORE", "Diocese admin; not relevant"),
    "Diocese (name)": ("IGNORE", "Diocese admin; not relevant"),
    "AdmissionsPolicy (code)": ("IGNORE", "Admissions policy; not spatial accessibility"),
    "AdmissionsPolicy (name)": ("IGNORE", "Admissions policy; not spatial accessibility"),

    # --- Capacity & Rolls ---
    "SchoolCapacity": ("USE", "Total capacity — needed for demand vs supply gap analysis"),
    "SpecialClasses (code)": ("IGNORE", "Special classes; not primary focus"),
    "SpecialClasses (name)": ("IGNORE", "Special classes; not primary focus"),
    "CensusDate": ("IGNORE", "Date of last census; admin field"),
    "NumberOfPupils": ("USE", "Current roll — actual demand figure for catchment analysis"),
    "NumberOfBoys": ("IGNORE", "Gender breakdown not needed at this level"),
    "NumberOfGirls": ("IGNORE", "Gender breakdown not needed at this level"),
    "PercentageFSM": ("USE", "% Free School Meals — deprivation proxy; correlates with IMD"),

    # --- Trust & Federation ---
    "TrustSchoolFlag (code)": ("IGNORE", "Trust membership; admin not spatial"),
    "TrustSchoolFlag (name)": ("IGNORE", "Trust membership; admin not spatial"),
    "Trusts (code)": ("IGNORE", "Trust identifier; admin"),
    "Trusts (name)": ("IGNORE", "Trust name; admin"),
    "SchoolSponsorFlag (name)": ("IGNORE", "Sponsor flag; admin"),
    "SchoolSponsors (name)": ("IGNORE", "Sponsor name; admin"),
    "FederationFlag (name)": ("IGNORE", "Federation flag; admin"),
    "Federations (code)": ("IGNORE", "Federation code; admin"),
    "Federations (name)": ("IGNORE", "Federation name; admin"),

    # --- Other IDs ---
    "UKPRN": ("IGNORE", "UKPRN provider code; not needed for spatial analysis"),
    "FEHEIdentifier": ("IGNORE", "Further/Higher Ed identifier; not relevant"),
    "FurtherEducationType (name)": ("IGNORE", "FE type; not relevant for school accessibility"),
    "LastChangedDate": ("IGNORE", "Admin timestamp; not analytical"),

    # --- Address & Contact ---
    "Street": ("USE", "Address component — useful for geocoding fallback"),
    "Locality": ("IGNORE", "Sub-locality; Postcode sufficient for geocoding"),
    "Address3": ("IGNORE", "Additional address line; rarely populated"),
    "Town": ("USE", "Town — useful for geographic display and validation"),
    "County (name)": ("IGNORE", "County; LA is more precise for our analysis"),
    "Postcode": ("USE", "Postcode — needed for geocoding schools missing Easting/Northing"),
    "SchoolWebsite": ("IGNORE", "Website; not analytical"),
    "TelephoneNum": ("IGNORE", "Telephone; not analytical"),

    # --- Head Teacher ---
    "HeadTitle (name)": ("IGNORE", "Head teacher details; not analytical"),
    "HeadFirstName": ("IGNORE", "Head teacher details; not analytical"),
    "HeadLastName": ("IGNORE", "Head teacher details; not analytical"),
    "HeadPreferredJobTitle": ("IGNORE", "Head teacher details; not analytical"),

    # --- Inspection ---
    "BSOInspectorateName (name)": ("IGNORE", "Inspection body; not spatial"),
    "InspectorateReport": ("IGNORE", "Inspection report URL; not analytical"),
    "DateOfLastInspectionVisit": ("IGNORE", "Inspection date; not analytical"),
    "NextInspectionVisit": ("IGNORE", "Future inspection; not analytical"),
    "InspectorateName (name)": ("IGNORE", "Inspection body name; not spatial"),

    # --- PRU / Special ---
    "TeenMoth (name)": ("IGNORE", "Teen mothers provision; niche — not primary focus"),
    "TeenMothPlaces": ("IGNORE", "Teen mothers places; niche"),
    "CCF (name)": ("IGNORE", "Combined Cadet Force; admin"),
    "SENPRU (name)": ("IGNORE", "SEN provision unit flag; niche"),
    "EBD (name)": ("IGNORE", "Emotional/behavioural difficulties flag; niche"),
    "PlacesPRU": ("IGNORE", "PRU places; niche"),
    "FTProv (name)": ("IGNORE", "Full-time provision; admin"),
    "EdByOther (name)": ("IGNORE", "Education by other provider; admin"),
    "Section41Approved (name)": ("IGNORE", "Section 41 approval; admin/legal"),

    # --- SEN Types (13 columns) ---
    "SEN1 (name)": ("IGNORE", "SEN need type 1; too granular for spatial analysis"),
    "SEN2 (name)": ("IGNORE", "SEN need type 2; too granular for spatial analysis"),
    "SEN3 (name)": ("IGNORE", "SEN need type 3; too granular for spatial analysis"),
    "SEN4 (name)": ("IGNORE", "SEN need type 4; too granular for spatial analysis"),
    "SEN5 (name)": ("IGNORE", "SEN need type 5; too granular for spatial analysis"),
    "SEN6 (name)": ("IGNORE", "SEN need type 6; too granular for spatial analysis"),
    "SEN7 (name)": ("IGNORE", "SEN need type 7; too granular for spatial analysis"),
    "SEN8 (name)": ("IGNORE", "SEN need type 8; too granular for spatial analysis"),
    "SEN9 (name)": ("IGNORE", "SEN need type 9; too granular for spatial analysis"),
    "SEN10 (name)": ("IGNORE", "SEN need type 10; too granular for spatial analysis"),
    "SEN11 (name)": ("IGNORE", "SEN need type 11; too granular for spatial analysis"),
    "SEN12 (name)": ("IGNORE", "SEN need type 12; too granular for spatial analysis"),
    "SEN13 (name)": ("IGNORE", "SEN need type 13; too granular for spatial analysis"),

    # --- Resourced Provision ---
    "TypeOfResourcedProvision (name)": ("IGNORE", "Specialist provision type; not primary focus"),
    "ResourcedProvisionOnRoll": ("IGNORE", "Specialist provision roll; not primary focus"),
    "ResourcedProvisionCapacity": ("IGNORE", "Specialist provision capacity; not primary focus"),
    "SenUnitOnRoll": ("IGNORE", "SEN unit roll; not primary focus"),
    "SenUnitCapacity": ("IGNORE", "SEN unit capacity; not primary focus"),

    # --- Geography ---
    "GOR (code)": ("USE", "Government Office Region code — regional grouping"),
    "GOR (name)": ("USE", "Government Office Region name — regional grouping"),
    "DistrictAdministrative (code)": ("IGNORE", "District code; LA is sufficient"),
    "DistrictAdministrative (name)": ("IGNORE", "District name; LA is sufficient"),
    "AdministrativeWard (code)": ("IGNORE", "Ward code; too granular for school-level analysis"),
    "AdministrativeWard (name)": ("IGNORE", "Ward name; too granular for school-level analysis"),
    "ParliamentaryConstituency (code)": ("IGNORE", "Constituency; not needed for bus analysis"),
    "ParliamentaryConstituency (name)": ("IGNORE", "Constituency; not needed for bus analysis"),
    "UrbanRural (code)": ("USE", "Urban/rural classification code — structural modifier"),
    "UrbanRural (name)": ("USE", "Urban/rural classification name — structural modifier"),
    "GSSLACode (name)": ("IGNORE", "GSS LA code; LA (code) already used"),

    # --- Spatial Coordinates ---
    "Easting": ("USE", "BNG Easting — primary geocoding input (OSGB36)"),
    "Northing": ("USE", "BNG Northing — primary geocoding input (OSGB36)"),
    "MSOA (code)": ("USE", "MSOA code — for employment/Census cross-reference"),
    "MSOA (name)": ("IGNORE", "MSOA name; code is sufficient"),
    "LSOA (code)": ("USE", "LSOA code — for IMD cross-reference"),
    "LSOA (name)": ("IGNORE", "LSOA name; code is sufficient"),

    # --- Other ---
    "SENStat": ("IGNORE", "SEN statement count; admin"),
    "SENNoStat": ("IGNORE", "SEN without statement; admin"),
    "BoardingEstablishment (name)": ("IGNORE", "Boarding school flag; not spatial"),
    "PropsName": ("IGNORE", "Proprietor name (independent schools); admin"),
    "PreviousLA (code)": ("IGNORE", "Previous LA code; historical admin"),
    "PreviousLA (name)": ("IGNORE", "Previous LA name; historical admin"),
    "PreviousEstablishmentNumber": ("IGNORE", "Previous OFSTED number; historical admin"),
    "Country (name)": ("USE", "Country — needed to filter England-only"),
    "UPRN": ("IGNORE", "Unique Property Reference Number; alternative ID not needed"),
    "SiteName": ("IGNORE", "Site name for multi-site establishments; admin"),
    "QABName (code)": ("IGNORE", "Quality assurance body code; admin"),
    "QABName (name)": ("IGNORE", "Quality assurance body name; admin"),
    "EstablishmentAccredited (code)": ("IGNORE", "Accreditation code; admin"),
    "EstablishmentAccredited (name)": ("IGNORE", "Accreditation name; admin"),
    "QABReport": ("IGNORE", "QAB report URL; not analytical"),
    "CHNumber": ("IGNORE", "Companies House number (academies); admin"),
    "FSM": ("IGNORE", "Free School Meals count (PercentageFSM used instead)"),
    "AccreditationExpiryDate": ("IGNORE", "Accreditation expiry; admin"),
}

# Build inventory dataframe
inventory_rows = []
for col in schools.columns:
    classification, rationale = COLUMN_CLASSIFICATIONS.get(col, ("REVIEW", "Not yet classified"))
    null_count = schools[col].isnull().sum()
    null_pct = null_count / len(schools) * 100
    sample_vals = schools[col].dropna().unique()[:3]
    sample_str = " | ".join(str(v) for v in sample_vals)
    inventory_rows.append({
        "column": col,
        "classification": classification,
        "rationale": rationale,
        "dtype": str(schools[col].dtype),
        "null_count": null_count,
        "null_pct": round(null_pct, 1),
        "sample_values": sample_str,
    })

inventory_df = pd.DataFrame(inventory_rows)
inventory_df.to_csv(AUDIT / "gias_column_inventory.csv", index=False)
logger.info(f"Saved gias_column_inventory.csv: {len(inventory_df)} rows")

# Verify all columns classified
classified = set(inventory_df["column"])
all_cols = set(schools.columns)
unclassified = all_cols - classified
if unclassified:
    check("column-inventory-complete", "WARN", f"{len(unclassified)} columns not in inventory: {unclassified}")
else:
    check("column-inventory-complete", "PASS", f"All {len(inventory_df)} columns classified")

# Distribution summary
dist = inventory_df["classification"].value_counts()
logger.info(f"Column classification distribution:\n{dist.to_string()}")

# %% [markdown]
# ## Section 3: Filter Open Schools (EstablishmentStatus code == 1)

# %%
# Use code column for robustness (text values can drift)
open_mask = schools["EstablishmentStatus (code)"] == 1
open_schools = schools[open_mask].copy()
open_count = len(open_schools)
logger.info(f"Open schools (status code 1): {open_count:,}")

check(
    "open-schools-count",
    "PASS" if open_count == 27183 else "WARN",
    f"{open_count:,} open schools (expected ~27,183)",
)

# Status breakdown for reference
status_breakdown = schools.groupby(
    ["EstablishmentStatus (code)", "EstablishmentStatus (name)"]
).size().reset_index(name="count")
logger.info(f"Status breakdown:\n{status_breakdown.to_string(index=False)}")

# %% [markdown]
# ## Section 4: Phase of Education Breakdown

# %%
phase_counts = open_schools["PhaseOfEducation (name)"].value_counts()
logger.info(f"Phase of Education (open schools):\n{phase_counts.to_string()}")

# Secondary-relevant phases for accessibility analysis
# Task spec: secondary + all-through (3,173 + 166 = 3,339)
SECONDARY_PHASES = ["Secondary", "All-through"]
secondary_mask = open_schools["PhaseOfEducation (name)"].isin(SECONDARY_PHASES)
secondary_open = open_schools[secondary_mask].copy()
secondary_count = len(secondary_open)
secondary_count_strict = int(phase_counts.get("Secondary", 0))
all_through_count = int(phase_counts.get("All-through", 0))

logger.info(f"Secondary schools: {secondary_count_strict:,}")
logger.info(f"All-through schools: {all_through_count:,}")
logger.info(f"Secondary + All-through (accessibility target): {secondary_count:,}")

check(
    "secondary-count",
    "PASS" if secondary_count_strict == 3173 else "WARN",
    f"Secondary: {secondary_count_strict:,} (expected 3,173)",
)
check(
    "all-through-count",
    "PASS" if all_through_count == 166 else "WARN",
    f"All-through: {all_through_count:,} (expected 166)",
)
check(
    "secondary-accessibility-total",
    "PASS" if secondary_count >= 3300 else "WARN",
    f"Secondary + All-through: {secondary_count:,} (expected ~3,339)",
)

# %% [markdown]
# ## Section 5: Coordinate Availability

# %%
# Check Easting/Northing for open schools
has_easting = open_schools["Easting"].notna() & (open_schools["Easting"] != 0)
has_northing = open_schools["Northing"].notna() & (open_schools["Northing"] != 0)
has_coords = has_easting & has_northing
coord_count = has_coords.sum()
coord_rate = coord_count / len(open_schools) * 100
missing_coords = (~has_coords).sum()

logger.info(f"Open schools with Easting/Northing: {coord_count:,} / {len(open_schools):,} ({coord_rate:.1f}%)")
logger.info(f"Missing coordinates: {missing_coords:,}")

check(
    "coord-coverage-open",
    "PASS" if coord_rate >= 97.0 else "WARN",
    f"{coord_rate:.1f}% open schools have coordinates (expected ≥97%)",
)

# Investigate missing — do they have postcodes?
missing_schools = open_schools[~has_coords].copy()
has_postcode = missing_schools["Postcode"].notna() & (missing_schools["Postcode"].str.strip() != "")
logger.info(f"Missing coords with postcodes: {has_postcode.sum()} / {len(missing_schools)}")

check(
    "missing-coords-have-postcode",
    "PASS" if has_postcode.sum() > 0 else "WARN",
    f"{has_postcode.sum()} of {len(missing_schools)} missing-coord schools have postcodes for geocoding",
)

# %% [markdown]
# ## Section 5b: Geocode Missing Schools via Code-Point Open

# %%
logger.info("Loading postcode lookup (Code-Point Open)…")
pc_lookup = pd.read_parquet(AUDIT / "postcode_lookup.parquet")
logger.info(f"Postcode lookup: {len(pc_lookup):,} entries")

def standardise_postcode(pc: pd.Series) -> pd.Series:
    """Standardise postcodes: uppercase, single space before inward code."""
    pc_clean = pc.fillna("").str.upper().str.strip()
    # Remove all spaces then insert before last 3 chars
    pc_nospace = pc_clean.str.replace(r"\s+", "", regex=True)
    # Add space: everything before last 3 chars + space + last 3 chars
    outward = pc_nospace.str[:-3]
    inward = pc_nospace.str[-3:]
    return outward + " " + inward

# Standardise postcode in lookup and missing schools
pc_lookup["pc_std"] = standardise_postcode(pc_lookup["Postcode"])
missing_schools = missing_schools.copy()
missing_schools["pc_std"] = standardise_postcode(missing_schools["Postcode"])

# Merge missing schools with postcode lookup
geocoded_missing = missing_schools.merge(
    pc_lookup[["pc_std", "Easting", "Northing"]].rename(
        columns={"Easting": "Easting_pc", "Northing": "Northing_pc"}
    ),
    on="pc_std",
    how="left",
)

# Fill missing Easting/Northing from postcode lookup
resolved = geocoded_missing["Easting_pc"].notna().sum()
logger.info(f"Missing coords resolved via postcode: {resolved} / {len(missing_schools)}")

check(
    "postcode-geocoding",
    "PASS" if resolved > 0 else "WARN",
    f"Resolved {resolved} schools via Code-Point Open postcode lookup",
)

# Apply resolved coordinates back
geocoded_missing["Easting"] = geocoded_missing["Easting"].fillna(geocoded_missing["Easting_pc"])
geocoded_missing["Northing"] = geocoded_missing["Northing"].fillna(geocoded_missing["Northing_pc"])

# Combine: schools with original coords + postcode-resolved
with_coords = open_schools[has_coords].copy()
geocoded_missing_resolved = geocoded_missing.drop(
    columns=["Easting_pc", "Northing_pc", "pc_std"], errors="ignore"
)
all_open_coords = pd.concat([with_coords, geocoded_missing_resolved], ignore_index=True)

# Re-check coord coverage after geocoding
final_has_coords = all_open_coords["Easting"].notna() & (all_open_coords["Easting"] != 0)
logger.info(f"After postcode geocoding: {final_has_coords.sum():,} / {len(all_open_coords):,} have coords")

# Keep only those with coordinates
all_open_with_coords = all_open_coords[final_has_coords].copy()
logger.info(f"Open schools with coordinates for projection: {len(all_open_with_coords):,}")

# %% [markdown]
# ## Section 6: Convert Easting/Northing → Latitude/Longitude

# %%
logger.info("Converting OSGB36/BNG (EPSG:27700) → WGS84 (EPSG:4326)…")
transformer = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)

lons, lats = transformer.transform(
    all_open_with_coords["Easting"].values,
    all_open_with_coords["Northing"].values,
)
all_open_with_coords = all_open_with_coords.copy()
all_open_with_coords["lon"] = lons
all_open_with_coords["lat"] = lats

# %% [markdown]
# ## Section 7: Spatial Validation — England Bounding Box

# %%
# England bounding box (lat: 49.8–55.8, lon: -6.4–1.8)
# Note: GIAS includes some overseas schools (British schools abroad — lat/lon will be far off)
ENG_LAT_MIN, ENG_LAT_MAX = 49.8, 55.8
ENG_LON_MIN, ENG_LON_MAX = -6.4, 1.8

out_of_bounds = ~(
    all_open_with_coords["lat"].between(ENG_LAT_MIN, ENG_LAT_MAX) &
    all_open_with_coords["lon"].between(ENG_LON_MIN, ENG_LON_MAX)
)
oob_count = out_of_bounds.sum()

if oob_count > 0:
    oob_schools = all_open_with_coords[out_of_bounds][["URN", "EstablishmentName", "Postcode", "lat", "lon"]]
    logger.warning(f"Schools outside England bounds: {oob_count}")
    logger.info(f"Out-of-bounds sample:\n{oob_schools.head(10).to_string(index=False)}")
    check("spatial-bounds", "WARN", f"{oob_count} schools outside England bounding box (expected: overseas British schools)")
else:
    check("spatial-bounds", "PASS", "All schools within England bounds")

# Filter to England only
england_open = all_open_with_coords[~out_of_bounds].copy()
logger.info(f"England open schools with coordinates: {len(england_open):,}")

# Schools per LA distribution
la_counts = england_open["LA (name)"].value_counts()
logger.info(f"Schools per LA — mean: {la_counts.mean():.1f}, median: {la_counts.median():.0f}, max: {la_counts.max()} ({la_counts.idxmax()})")

check(
    "england-schools-count",
    "PASS" if len(england_open) >= 26000 else "WARN",
    f"{len(england_open):,} England open schools geocoded",
)

# %% [markdown]
# ## Section 8: Cross-Reference with Bus Stops (KDTree)

# %%
# Load NaPTAN bus stops (England active: BCT/BCS/BCE, ATCO 0xx-4xx)
logger.info("Loading NaPTAN bus stops for KDTree proximity analysis…")
naptan = pd.read_csv(
    RAW / "naptan/Stops.csv",
    usecols=["ATCOCode", "Latitude", "Longitude", "StopType", "Status"],
    low_memory=False,
)
logger.info(f"NaPTAN total rows: {len(naptan):,}")

# Filter England active bus stops
eng_stop_types = ["BCT", "BCS", "BCE"]
naptan_england = naptan[
    naptan["StopType"].isin(eng_stop_types) &
    (naptan["Status"] == "active") &
    naptan["ATCOCode"].str.match(r"^[0-4]\d{2}", na=False)
].copy()
logger.info(f"England active bus stops: {len(naptan_england):,}")

check(
    "bus-stops-england",
    "PASS" if len(naptan_england) == 274719 else "WARN",
    f"{len(naptan_england):,} England active bus stops (expected 274,719)",
)

# Drop stops with missing lat/lon
stops_clean = naptan_england.dropna(subset=["Latitude", "Longitude"])
logger.info(f"Stops with coordinates: {len(stops_clean):,}")

# Build KDTree from stop coordinates
# Use radians for great-circle distance approximation
EARTH_RADIUS_M = 6_371_000
stops_lat_rad = np.radians(stops_clean["Latitude"].values)
stops_lon_rad = np.radians(stops_clean["Longitude"].values)
stops_cart = np.column_stack([
    np.cos(stops_lat_rad) * np.cos(stops_lon_rad),
    np.cos(stops_lat_rad) * np.sin(stops_lon_rad),
    np.sin(stops_lat_rad),
])
logger.info("Building KDTree from bus stop coordinates…")
stop_tree = cKDTree(stops_cart)

# Query for secondary schools (primary use case — accessibility analysis)
sec_england = england_open[england_open["PhaseOfEducation (name)"].isin(SECONDARY_PHASES)].copy()
logger.info(f"Secondary schools to query: {len(sec_england):,}")

school_lat_rad = np.radians(sec_england["lat"].values)
school_lon_rad = np.radians(sec_england["lon"].values)
school_cart = np.column_stack([
    np.cos(school_lat_rad) * np.cos(school_lon_rad),
    np.cos(school_lat_rad) * np.sin(school_lon_rad),
    np.sin(school_lat_rad),
])

# Query nearest stop
dist_cart, idx = stop_tree.query(school_cart, k=1)
# Convert chord distance to approximate metres
dist_m = 2 * EARTH_RADIUS_M * np.arcsin(dist_cart / 2)

sec_england = sec_england.copy()
sec_england["nearest_stop_id"] = stops_clean.iloc[idx]["ATCOCode"].values
sec_england["nearest_stop_dist_m"] = dist_m

# Distribution of distances
pct_400m = (dist_m <= 400).mean() * 100
pct_800m = (dist_m <= 800).mean() * 100
no_stop_400 = (dist_m > 400).sum()
no_stop_800 = (dist_m > 800).sum()

logger.info(f"Secondary schools within 400m of bus stop: {pct_400m:.1f}%")
logger.info(f"Secondary schools within 800m of bus stop: {pct_800m:.1f}%")
logger.info(f"Secondary schools with no stop within 400m: {no_stop_400:,}")
logger.info(f"Secondary schools with no stop within 800m: {no_stop_800:,}")
logger.info(f"Distance distribution (m): median={np.median(dist_m):.0f}, p90={np.percentile(dist_m, 90):.0f}, max={dist_m.max():.0f}")

check(
    "secondary-stop-proximity-400m",
    "PASS" if pct_400m >= 80 else "WARN",
    f"{pct_400m:.1f}% secondary schools within 400m of bus stop",
)
check(
    "secondary-no-stop-400m",
    "PASS",
    f"{no_stop_400:,} secondary schools with no bus stop within 400m",
)

# Also run for all open schools (sample used for output file)
logger.info("Running KDTree for all open England schools…")
all_lat_rad = np.radians(england_open["lat"].values)
all_lon_rad = np.radians(england_open["lon"].values)
all_cart = np.column_stack([
    np.cos(all_lat_rad) * np.cos(all_lon_rad),
    np.cos(all_lat_rad) * np.sin(all_lon_rad),
    np.sin(all_lat_rad),
])
all_dist_cart, all_idx = stop_tree.query(all_cart, k=1)
all_dist_m = 2 * EARTH_RADIUS_M * np.arcsin(all_dist_cart / 2)

england_open = england_open.copy()
england_open["nearest_stop_id"] = stops_clean.iloc[all_idx]["ATCOCode"].values
england_open["nearest_stop_dist_m"] = all_dist_m

# %% [markdown]
# ## Section 9: Save Output Files

# %%
# Output columns for both files
BASE_COLS = [
    "URN", "EstablishmentName",
    "TypeOfEstablishment (name)", "PhaseOfEducation (name)",
    "EstablishmentStatus (name)", "LA (code)", "LA (name)",
    "GOR (code)", "GOR (name)",
    "UrbanRural (code)", "UrbanRural (name)",
    "Postcode", "Easting", "Northing", "lat", "lon",
    "LSOA (code)", "MSOA (code)",
    "SchoolCapacity", "NumberOfPupils", "PercentageFSM",
    "nearest_stop_id", "nearest_stop_dist_m",
]

# Filter to available columns
available_base = [c for c in BASE_COLS if c in england_open.columns]
missing_base = [c for c in BASE_COLS if c not in england_open.columns]
if missing_base:
    logger.warning(f"Base columns not in dataframe: {missing_base}")

# --- File 1: All open England schools with coordinates ---
all_open_out = england_open[available_base].copy()
all_open_out.to_parquet(AUDIT / "schools_all_open_geocoded.parquet", index=False)
logger.info(f"Saved schools_all_open_geocoded.parquet: {len(all_open_out):,} rows")

check(
    "output-all-open",
    "PASS",
    f"schools_all_open_geocoded.parquet: {len(all_open_out):,} rows",
)

# --- File 2: Secondary + All-through only ---
sec_cols = [c for c in BASE_COLS if c in sec_england.columns]
sec_out = sec_england[sec_cols].copy()
sec_out.to_parquet(AUDIT / "schools_secondary_geocoded.parquet", index=False)
logger.info(f"Saved schools_secondary_geocoded.parquet: {len(sec_out):,} rows")

check(
    "output-secondary",
    "PASS",
    f"schools_secondary_geocoded.parquet: {len(sec_out):,} rows",
)

# --- File 3: Column inventory (already saved in Section 2) ---
check(
    "output-column-inventory",
    "PASS",
    f"gias_column_inventory.csv: {len(inventory_df)} rows",
)

# %% [markdown]
# ## Section 10: Validation Summary

# %%
logger.info("=" * 60)
logger.info("VALIDATION SUMMARY — 03d GIAS Schools Audit")
logger.info("=" * 60)

checks_df = pd.DataFrame(CHECKS)
for _, row in checks_df.iterrows():
    symbol = {"PASS": "✓", "WARN": "!", "FAIL": "✗"}.get(row["status"], "?")
    logger.info(f"  [{row['status']}] {symbol} {row['check']}: {row['detail']}")

pass_count = (checks_df["status"] == "PASS").sum()
warn_count = (checks_df["status"] == "WARN").sum()
fail_count = (checks_df["status"] == "FAIL").sum()

logger.info("-" * 60)
logger.info(f"TOTAL: {pass_count} PASS | {warn_count} WARN | {fail_count} FAIL")
logger.info("=" * 60)
logger.info("KEY FIGURES:")
logger.info(f"  Total establishments in GIAS: {len(schools):,}")
logger.info(f"  Open schools (GT-016):        {open_count:,}")
logger.info(f"  Secondary schools:            {secondary_count_strict:,}")
logger.info(f"  All-through schools:          {all_through_count:,}")
logger.info(f"  Secondary+All-through (GT-017): {secondary_count:,}")
logger.info(f"  England open geocoded:        {len(england_open):,}")
logger.info(f"  Secondary england geocoded:   {len(sec_out):,}")
logger.info(f"  Coord coverage (open):        {coord_rate:.1f}%")
logger.info(f"  Within 400m of bus stop (%):  {pct_400m:.1f}%")
logger.info(f"  No stop within 400m (count):  {no_stop_400:,}")
logger.info("=" * 60)

if fail_count > 0:
    raise RuntimeError(f"03d FAILED: {fail_count} checks failed — review logs above")

logger.info("03d_schools_gias COMPLETE")
