"""Netherlands geography, OVapi evening window, and official download URLs."""

from __future__ import annotations

# OVapi national GTFS (bus + rail + metro + tram + ferry). Gitignore the zip.
# Last-Modified documented at download time (see CURRENT_STATE Wave 7).
OVAPI_GTFS_URL = "https://gtfs.ovapi.nl/nl/gtfs-nl.zip"
OVAPI_GTFS_URL_ALT = "https://gtfs.ovapi.nl/gtfs-nl.zip"

# CBS SES-WOA StatLine 86092NED — scores per wijk/buurt, regio-indeling 2024.
# Periods 2014–2023. We take 2023 (voorlopig). Buurt codes start with BU.
SES_WOA_TABLE = "86092NED"
SES_WOA_YEAR = "2023"
SES_WOA_PERIOD = "2023JJ00"
SES_WOA_ODATA = "https://opendata.cbs.nl/ODataApi/odata/86092NED"
SES_WOA_TYPED = "https://opendata.cbs.nl/ODataFeed/odata/86092NED/TypedDataSet"

# CBS Kerncijfers wijken en buurten 2024 (matches SES 2024 regio-indeling).
KERNCIJFERS_TABLE = "85984NED"
KERNCIJFERS_ODATA = "https://opendata.cbs.nl/ODataApi/odata/85984NED"
KERNCIJFERS_TYPED = "https://opendata.cbs.nl/ODataFeed/odata/85984NED/TypedDataSet"

# CBS Wijk- en Buurtkaart 2024 v2 — geometry + stedelijkheid attributes.
WIJKBUURT_2024_URL = "https://geodata.cbs.nl/files/Wijkenbuurtkaart/WijkBuurtkaart_2024_v2.zip"
WIJKBUURT_2025_URL = "https://geodata.cbs.nl/files/Wijkenbuurtkaart/WijkBuurtkaart_2025_v1.zip"

# PDOK WFS (fallback if the zip 404s).
PDOK_WFS_2024 = (
    "https://service.pdok.nl/cbs/wijkenbuurten/2024/wfs/v1_0"
    "?service=WFS&version=2.0.0&request=GetFeature&typeNames=cbs:buurten"
    "&outputFormat=application/json&srsName=EPSG:4326"
)

# Twelve provincies. English display names; slugs are lowercase hyphenated.
NL_PROVINCES: list[tuple[str, str]] = [
    ("drenthe", "Drenthe"),
    ("flevoland", "Flevoland"),
    ("friesland", "Fryslân"),
    ("gelderland", "Gelderland"),
    ("groningen", "Groningen"),
    ("limburg", "Limburg"),
    ("noord-brabant", "Noord-Brabant"),
    ("noord-holland", "Noord-Holland"),
    ("overijssel", "Overijssel"),
    ("utrecht", "Utrecht"),
    ("zeeland", "Zeeland"),
    ("zuid-holland", "Zuid-Holland"),
]

PROVINCE_NAME_BY_SLUG: dict[str, str] = {s: n for s, n in NL_PROVINCES}
PROVINCE_SLUG_BY_NAME: dict[str, str] = {n.lower(): s for s, n in NL_PROVINCES}

# Mainland + Wadden, WGS84. BE/DE stops fall outside.
NL_BBOX = (3.20, 50.75, 7.22, 53.70)  # west, south, east, north

EVENING_START_MIN = 19 * 60
NL_EVENING_NOTE = (
    "Evening on the Netherlands pack is departures at or after 19:00 on an OVapi "
    "weekday calendar date. OVapi does not publish a separate evening product."
)

# Official CBS stedelijkheid (1 = zeer stedelijk … 5 = niet stedelijk).
# Urban = 1–3; rural = 4–5. Not Ireland’s 150/km² rule.
URBAN_STEDELIJKHEID_MAX = 3
STEDELIJKHEID_NOTE = (
    "Urban/rural is official CBS mate van stedelijkheid (1–3 urban, 4–5 rural). "
    "Not a density copy from another country."
)

# GTFS route_type: bus-comparable vs all public transport in the OVapi zip.
BUS_ROUTE_TYPES = frozenset({3, 11, *range(700, 800)})
ALL_PT_ROUTE_TYPES = frozenset(
    {0, 1, 2, 3, 4, 5, 6, 7, 11, 12, *range(100, 200), *range(200, 300), *range(400, 500), *range(700, 800), *range(900, 1000)}
)

RDNEW = "EPSG:28992"


def in_nl_bbox(lat: float, lon: float) -> bool:
    west, south, east, north = NL_BBOX
    return south <= lat <= north and west <= lon <= east


def slug_province(name: str) -> str:
    if name is None or (isinstance(name, float) and name != name):
        return "unknown"
    key = str(name).strip().lower().replace("provincie ", "")
    aliases = {
        "fryslân": "friesland",
        "fryslan": "friesland",
        "friesland": "friesland",
        "noord holland": "noord-holland",
        "noordholland": "noord-holland",
        "zuid holland": "zuid-holland",
        "zuidholland": "zuid-holland",
        "noord brabant": "noord-brabant",
        "noordbrabant": "noord-brabant",
        "n-holland": "noord-holland",
        "z-holland": "zuid-holland",
        "nh": "noord-holland",
        "zh": "zuid-holland",
        "nb": "noord-brabant",
    }
    if key in PROVINCE_SLUG_BY_NAME:
        return PROVINCE_SLUG_BY_NAME[key]
    if key in PROVINCE_NAME_BY_SLUG:
        return key
    return aliases.get(key, key.replace(" ", "-"))
