"""France geography, NAP evening window, official download URLs (only URLs we hit)."""

from __future__ import annotations

# NAP catalog — format=gtfs is filtered client-side (API ignores ?format=).
NAP_DATASETS_URL = "https://transport.data.gouv.fr/api/datasets"

# IGN Geoplateforme WFS — CONTOURS IRIS. numberMatched=49386 on 2026-08-17.
IGN_IRIS_WFS = (
    "https://data.geopf.fr/wfs/ows"
    "?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
    "&TYPENAMES=STATISTICALUNITS.IRIS:contours_iris"
    "&outputFormat=application/json"
)
IGN_IRIS_WFS_HITS = (
    "https://data.geopf.fr/wfs/ows"
    "?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
    "&TYPENAMES=STATISTICALUNITS.IRIS:contours_iris&resultType=hits"
)

# F-EDI 2021 IRIS — data.gouv resource id (redirect). Geography IRIS 01.01.2023.
FEDI_DATASET_SLUG = (
    "indice-de-defavorisation-sociale-edi-european-deprivation-index-"
    "pour-la-france-metropolitaine-version-2021"
)
FEDI_IRIS_RESOURCE = "https://www.data.gouv.fr/api/1/datasets/r/8c8b3425-b6bf-40d5-8e02-559d40d687a6"
FEDI_COMMUNE_RESOURCE = "https://www.data.gouv.fr/api/1/datasets/r/e507b4c1-da47-40f6-a006-ed1048d55cc5"

# INSEE recensement IRIS 2018 + grille de densité 7 niveaux 2024.
INSEE_IRIS_POP_ZIP = (
    "https://www.insee.fr/fr/statistiques/fichier/5650720/base-ic-evol-struct-pop-2018_csv.zip"
)
INSEE_DENSITY_XLSX = (
    "https://www.insee.fr/fr/statistiques/fichier/6439600/grille_densite_7_niveaux_2024.xlsx"
)

# Filosofi IRIS — tried; may 404. Do not invent a second path.
FILOSOFI_IRIS_CANDIDATES = (
    "https://www.insee.fr/fr/statistiques/fichier/8229323/BASE_TD_FILO_DISP_IRIS_2021.xlsx",
    "https://www.insee.fr/fr/statistiques/fichier/6692218/BASE_TD_FILO_DISP_IRIS_2020.xlsx",
    "https://www.insee.fr/fr/statistiques/fichier/6036907/BASE_TD_FILO_DISP_IRIS_2019.xlsx",
)

# 13 metropolitan régions. Slugs match france-geojson `nom` folded (Fryslân trap).
FR_REGIONS: list[tuple[str, str, str]] = [
    ("auvergne-rhone-alpes", "Auvergne-Rhône-Alpes", "84"),
    ("bourgogne-franche-comte", "Bourgogne-Franche-Comté", "27"),
    ("bretagne", "Bretagne", "53"),
    ("centre-val-de-loire", "Centre-Val de Loire", "24"),
    ("corse", "Corse", "94"),
    ("grand-est", "Grand Est", "44"),
    ("hauts-de-france", "Hauts-de-France", "32"),
    ("ile-de-france", "Île-de-France", "11"),
    ("normandie", "Normandie", "28"),
    ("nouvelle-aquitaine", "Nouvelle-Aquitaine", "75"),
    ("occitanie", "Occitanie", "76"),
    ("pays-de-la-loire", "Pays de la Loire", "52"),
    ("provence-alpes-cote-dazur", "Provence-Alpes-Côte d'Azur", "93"),
]

REGION_NAME_BY_SLUG: dict[str, str] = {s: n for s, n, _ in FR_REGIONS}
REGION_SLUG_BY_CODE: dict[str, str] = {c: s for s, _n, c in FR_REGIONS}
REGION_SLUG_BY_NAME: dict[str, str] = {n.lower(): s for s, n, _c in FR_REGIONS}

# Mainland + Corsica WGS84. DOM out.
FR_BBOX = (-5.20, 41.30, 9.70, 51.20)  # west, south, east, north

EVENING_START_MIN = 19 * 60
FR_EVENING_NOTE = (
    "Evening on the France pack is departures at or after 19:00 on a NAP weekday "
    "calendar date. NAP feeds do not share one evening product."
)

# INSEE grille de densité 7 niveaux (2024, géographie 01/01/2024).
# 1–4 = centres + ceintures urbaines; 5–7 = bourgs ruraux + rural dispersé.
URBAN_DENSITY_MAX = 4
DENSITY_NOTE = (
    "Urban/rural is official INSEE grille communale de densité 7 niveaux (2024): "
    "levels 1–4 urban (grands/centres/petites villes/ceintures), 5–7 rural "
    "(bourgs + habitat dispersé). Joined commune → IRIS. Not Ireland’s 150/km² "
    "and not CBS stedelijkheid."
)

BUS_ROUTE_TYPES = frozenset({3, 11, *range(700, 800)})
ALL_PT_ROUTE_TYPES = frozenset(
    {
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        11,
        12,
        *range(100, 200),
        *range(200, 300),
        *range(400, 500),
        *range(700, 800),
        *range(900, 1000),
    }
)

LAMBERT93 = "EPSG:2154"

# Mainland départements 01–95 (Corsica 2A/2B). 20 unused (became 2A/2B).
MAINLAND_DEPS = [f"{i:02d}" for i in range(1, 20)] + ["2A", "2B"] + [f"{i:02d}" for i in range(21, 96)]


def in_fr_bbox(lat: float, lon: float) -> bool:
    west, south, east, north = FR_BBOX
    return south <= lat <= north and west <= lon <= east


def slug_region(name: str) -> str:
    if name is None or (isinstance(name, float) and name != name):
        return "unknown"
    key = str(name).strip().lower()
    key = (
        key.replace("île", "ile")
        .replace("î", "i")
        .replace("ô", "o")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ç", "c")
        .replace("'", "")
        .replace("’", "")
    )
    aliases = {
        "ile-de-france": "ile-de-france",
        "ile de france": "ile-de-france",
        "provence-alpes-cote dazur": "provence-alpes-cote-dazur",
        "provence-alpes-cote-d-azur": "provence-alpes-cote-dazur",
        "paca": "provence-alpes-cote-dazur",
        "auvergne rhone alpes": "auvergne-rhone-alpes",
        "bourgogne franche comte": "bourgogne-franche-comte",
        "centre val de loire": "centre-val-de-loire",
        "hauts de france": "hauts-de-france",
        "nouvelle aquitaine": "nouvelle-aquitaine",
        "pays de la loire": "pays-de-la-loire",
        "grand est": "grand-est",
    }
    folded = key.replace(" ", "-")
    if folded in REGION_NAME_BY_SLUG:
        return folded
    if key in REGION_SLUG_BY_NAME:
        return REGION_SLUG_BY_NAME[key]
    return aliases.get(folded, folded)


def region_from_insee_reg(code: object) -> str:
    s = str(code or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    if len(s) == 1:
        s = s.zfill(2)
    return REGION_SLUG_BY_CODE.get(s, slug_region(s))


def iris_text(raw: object) -> str:
    s = str(raw or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    digits = "".join(ch for ch in s if ch.isdigit() or ch in "AB")
    if len(digits) >= 9:
        return digits[:9]
    if digits.isdigit():
        return digits.zfill(9)
    return s.zfill(9) if s else ""
