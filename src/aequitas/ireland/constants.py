"""Republic-only geography, TFI evening window, and official download URLs."""

from __future__ import annotations

# TFI static GTFS (all operators). Gitignore the zip.
TFI_GTFS_URL = "https://www.transportforireland.ie/transitData/Data/GTFS_All.zip"

# Pobal HP 2022 — official ED scores (CKAN datastore first: pobal.ie times out).
# Resource 0806f07b-b514-4769-bd3d-649da87ad205 is ED-level (3,417 rows), not SA.
# SA-level HP is not published as a free CSV on data.gov.ie; we join SA→ED.
POBAL_HP_2022_CKAN_DUMP = (
    "https://data.gov.ie/datastore/dump/0806f07b-b514-4769-bd3d-649da87ad205"
)
POBAL_HP_2022_URLS = (
    POBAL_HP_2022_CKAN_DUMP,
    # data.gov.ie CKAN file URL (302 → pobal.ie; often times out)
    "https://data.gov.ie/dataset/91d486e0-b233-4603-891b-37f10748d0bc/resource/"
    "0806f07b-b514-4769-bd3d-649da87ad205/download/hp-deprivation-index-scores-2022.csv",
    "https://www.pobal.ie/wp-content/uploads/2024/01/hp-deprivation-index-scores-2022.csv",
    "https://www.pobal.ie/app/uploads/2024/01/hp-deprivation-index-scores-2022.csv",
    "https://www.pobal.ie/wp-content/uploads/2024/01/hp-deprivation-index-scores-2022-1-1.xlsx",
)

# OSi / CSO county polygons (Republic). Used for the home map — not boxes.
IRELAND_COUNTY_GEOJSON_URLS = (
    "https://services-eu1.arcgis.com/PxbTDTskGHCe4sv6/arcgis/rest/services/"
    "Counties___OSi_National_Statutory_Boundaries___Generalised_20m/FeatureServer/0/"
    "query?where=1%3D1&outFields=*&f=geojson",
    "https://data-osi.opendata.arcgis.com/datasets/"
    "osi::counties-national-statutory-boundaries-2019-generalised-20m.geojson",
)

# CSO / OSi Small Areas 2022 (Republic). Tried in order; first 200 wins.
CSO_SA_2022_URLS = (
    # Tailte Éireann / ArcGIS Hub packaged GeoJSON (generalised 20 m)
    "https://opendata.arcgis.com/api/v3/datasets/438ebc805bfc4ec2843cc69a75d463a3/"
    "downloads/data?format=geojson&spatialRefId=4326",
    "https://opendata.arcgis.com/api/v3/datasets/7ff6cde006db4a98876c58de49f108b1_0/"
    "downloads/data?format=geojson&spatialRefId=4326",
    "https://data-osi.opendata.arcgis.com/datasets/"
    "osi::cso-small-areas-national-statistical-boundaries-2022-generalised-20m.geojson",
    "https://data-osi.opendata.arcgis.com/datasets/"
    "osi::cso-small-areas-national-statistical-boundaries-2022-ungeneralised.geojson",
)

# Census 2022 SAPS population (CSO PxStat CSV) — T1 T1 usually total persons.
CSO_SAPS_POP_URLS = (
    # Official CSO Census 2022 SA file (18,919 SAs + urban/rural)
    "https://www.cso.ie/en/media/csoie/census/census2022/SAPS_2022_Small_Area_UR_171024.csv",
    "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/SAP2022T1T1ALY/CSV/1.0/en",
)

# Republic counties (26). English names. No NI.
IRELAND_COUNTIES: list[tuple[str, str]] = [
    ("carlow", "Carlow"),
    ("cavan", "Cavan"),
    ("clare", "Clare"),
    ("cork", "Cork"),
    ("donegal", "Donegal"),
    ("dublin", "Dublin"),
    ("galway", "Galway"),
    ("kerry", "Kerry"),
    ("kildare", "Kildare"),
    ("kilkenny", "Kilkenny"),
    ("laois", "Laois"),
    ("leitrim", "Leitrim"),
    ("limerick", "Limerick"),
    ("longford", "Longford"),
    ("louth", "Louth"),
    ("mayo", "Mayo"),
    ("meath", "Meath"),
    ("monaghan", "Monaghan"),
    ("offaly", "Offaly"),
    ("roscommon", "Roscommon"),
    ("sligo", "Sligo"),
    ("tipperary", "Tipperary"),
    ("waterford", "Waterford"),
    ("westmeath", "Westmeath"),
    ("wexford", "Wexford"),
    ("wicklow", "Wicklow"),
]

COUNTY_NAME_BY_SLUG: dict[str, str] = {s: n for s, n in IRELAND_COUNTIES}
COUNTY_SLUG_BY_NAME: dict[str, str] = {n.lower(): s for s, n in IRELAND_COUNTIES}

# Republic bbox (WGS84). NI is clipped separately (see in_northern_ireland).
IRELAND_BBOX = (-10.8, 51.25, -5.88, 55.45)  # west, south, east, north

# Evening = departures at or after 19:00. TFI calendars use clock times;
# we do not invent a TFI-specific “evening” product — this is the same
# 19:00 last-service threshold as the England evening-isolated flag.
EVENING_START_MIN = 19 * 60
IRELAND_EVENING_NOTE = (
    "Evening on the Ireland pack is departures at or after 19:00 on a TFI "
    "weekday calendar date. TFI does not publish a separate evening product."
)

# Density rule (CSO urban/rural classification is not a free SA CSV here).
# Documented as such — not England RUC codes.
URBAN_DENSITY_PER_KM2 = 150.0
URBAN_RURAL_NOTE = (
    "Urban/rural is a documented density rule (people per km² ≥ 150 = urban). "
    "Not England RUC codes."
)

# Approximate NI box that does not swallow Donegal (west of −8.18).
# Used only when a point is not inside a Republic county polygon.
_NI_WEST, _NI_SOUTH, _NI_EAST, _NI_NORTH = (-8.18, 54.02, -5.40, 55.32)


def in_ireland_bbox(lat: float, lon: float) -> bool:
    west, south, east, north = IRELAND_BBOX
    return south <= lat <= north and west <= lon <= east


def in_northern_ireland(lat: float, lon: float) -> bool:
    """Conservative NI test. Donegal (west of −8.18) stays in the Republic."""
    return _NI_SOUTH <= lat <= _NI_NORTH and _NI_WEST <= lon <= _NI_EAST


def slug_county(name: str) -> str:
    key = (name or "").strip().lower().replace("county ", "")
    if key in COUNTY_SLUG_BY_NAME:
        return COUNTY_SLUG_BY_NAME[key]
    if key in COUNTY_NAME_BY_SLUG:
        return key
    # Common CSO variants
    aliases = {
        "co. dublin": "dublin",
        "south dublin": "dublin",
        "fingal": "dublin",
        "dun laoghaire-rathdown": "dublin",
        "dún laoghaire-rathdown": "dublin",
        "dun-laoghaire/rathdown": "dublin",
        "dun laoghaire/rathdown": "dublin",
        "dún laoghaire/rathdown": "dublin",
        "dlr": "dublin",
        "north tipperary": "tipperary",
        "south tipperary": "tipperary",
        "north-tipperary": "tipperary",
        "south-tipperary": "tipperary",
        "dublin city": "dublin",
        "cork city": "cork",
        "cork county": "cork",
        "galway city": "galway",
        "galway county": "galway",
        "limerick city": "limerick",
        "limerick city and county": "limerick",
        "waterford city": "waterford",
        "waterford city and county": "waterford",
        "tipperary north": "tipperary",
        "tipperary south": "tipperary",
    }
    return aliases.get(key, key.replace(" ", "-"))
