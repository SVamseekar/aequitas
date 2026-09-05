# France Wave 9 — source log

Fetched **2026-08-17**. Only URLs actually hit. Status and counts are measured.
Never invent a second URL. £0 only. Metropolitan France; DOM out unless both IRIS + GTFS exist (they do not in this harvest).

## A. Network — NAP (transport.data.gouv.fr)

| URL | Date | HTTP | Bytes / rows | Notes |
|-----|------|------|--------------|-------|
| `https://transport.data.gouv.fr/api/datasets` | 2026-08-17 | **200** | 2,477,986 B JSON; **774** datasets | Full catalog (format query is ignored; client-side filter required) |
| `https://transport.data.gouv.fr/api/datasets?format=gtfs` | 2026-08-17 | **200** | same 2,477,986 B | Query param does **not** filter; still the full catalog |
| `https://transport.data.gouv.fr/api/stats` | 2026-08-17 | **200** | 2,166,449 B GeoJSON | Coverage polygons (includes DOM e.g. New Caledonia) — not used as GTFS |

**GTFS resources in catalog:** **552** (`format=gtfs`). **548** `is_available=true`, **4** unavailable.
**Datasets with ≥1 GTFS:** 475.
**Known filesize sum (subset that publish size):** 281.8 MB. Many resources omit `filesize`.
**GTFS-RT:** 380 resources listed — **not harvested** (Wave 8 / later).
**Region tags on GTFS resources:** every GTFS resource had empty `regions` in this API snapshot (`(none)` = 552). Coverage logging is therefore **by stop bbox + INSEE département**, not NAP region tags.

Catalog snapshot: `data/france/nap_gtfs_catalog.json` (552 rows).

### Harvest policy (this wave)

- Download every available GTFS zip from the catalog.
- Prefix `stop_id` / `trip_id` / `route_id` / `agency_id` with `dataset_id` to avoid collisions.
- Clip stops to metropolitan bbox `FR_BBOX = (−5.2, 41.3, 9.7, 51.2)`. Corsica in bbox. DOM (971–976) **out**.
- `calendar.txt` is **not assumed**. Sunday / weekday flags come from `calendar.txt` **or** `calendar_dates.txt` (`exception_type=1`) — NL trap #10.
- `mode=bus` = GTFS `route_type` bus-comparable; then append `mode=all`.
- Missing départements: logged after merge (mainland 01–95, Corsica 2A/2B). A département with zero stops inside the bbox is **logged missing**, not invented as 0% coverage.
- If a resource 404s / times out: skip, increment `skipped`, write URL + status. Never invent a replacement URL.

Partial harvest is allowed only with `packReady=false` and UI sentence “partial harvest — N départements logged missing.”

## B. Small area — IRIS

| URL | Date | HTTP | Count | Join key |
|-----|------|------|-------|----------|
| `https://www.data.gouv.fr/api/1/datasets/?q=CONTOURS%20IRIS%202024` | 2026-08-17 | **200** | 1 hit | slug `contours-iris-geographie-2024` is **Bordeaux Métropole only** — not national |
| `https://www.data.gouv.fr/api/1/datasets/contours-iris/` | 2026-08-17 | **200** | IGN WFS/WMS links | National IGN Contours IRIS |
| `https://www.data.gouv.fr/api/1/datasets/contours-iris-r-2/` | 2026-08-17 | **200** | same IGN | `last_update` 2026-04-30 |
| `https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities` | 2026-08-17 | **200** | 5,180,577 B | Layer `STATISTICALUNITS.IRIS:contours_iris` |
| WFS `GetFeature` `TYPENAMES=STATISTICALUNITS.IRIS:contours_iris` `resultType=hits` | 2026-08-17 | **200** | **`numberMatched=49386`** | Props: `code_iris` (9-digit text), `code_insee`, `nom_commune`, `nom_iris`, `type_iris` |
| WFS `CONTOURS-IRIS:contours_iris` | 2026-08-17 | **400** | ExceptionReport | Wrong typename — do not retry as if it worked |
| `https://www.data.gouv.fr/api/1/datasets/base-des-iris/` | 2026-08-17 | **404** | — | Does not exist |

**Verified IRIS n (IGN WFS vintage on 2026-08-17): 49,386.** Do not hardcode 18,919 or 13,827.

Metropolitan filter: drop `code_insee` starting with 97 (DOM) unless a later wave has both IRIS + GTFS. Residual vs F-EDI IRIS file is documented in §C.

Population vintage: INSEE recensement IRIS **2018** (`base-ic-evol-struct-pop-2018`) — not the same vintage as IGN contours (live WFS) or F-EDI IRIS geography 01.01.2023. Mismatch is documented, not patched.

## C. Deprivation — official first

Tried in order (data.gouv.fr search, 2026-08-17):

| Query / URL | HTTP | Result |
|-------------|------|--------|
| `q=F-EDI` | **200** | 0 datasets (hyphenated string) |
| `q=indice depriv` | **200** | **F-EDI / EDI** 2011, 2015, 2017, **2021** |
| `q=FDep IRIS` | **200** | 0 |
| `q=GISD IRIS` | **200** | 0 |
| `q=filosofi` | **200** | 5 hits, **none** IRIS Filosofi table (carroyage / commune / bureau de vote only) |

**Official index used: EDI 2021 (F-EDI) at IRIS.**

| URL | HTTP | Bytes | Rows | Join |
|-----|------|-------|------|------|
| `https://www.data.gouv.fr/api/1/datasets/indice-de-defavorisation-sociale-edi-european-deprivation-index-pour-la-france-metropolitaine-version-2021/` | **200** | metadata | 2 resources | IRIS + commune |
| `https://www.data.gouv.fr/api/1/datasets/r/8c8b3425-b6bf-40d5-8e02-559d40d687a6` → `…/20250919-135351/edi2021-iris-fm.xlsx` | **200** | **2,408,872** | **48,577** IRIS (`EDI2021_IRIS`) | `IRIS` 9-digit text |
| Guessed path `…/20250919-134554/edi2021-iris-fm.xlsx` | **404** | 0 | — | Do not use |
| Commune file `…/r/e507b4c1-da47-40f6-a006-ed1048d55cc5` | **200** | 1,627,708 | 34,848 communes | `CODGEO` — **not** used to invent IRIS deciles |

Columns IRIS: `IRIS, REG, DEP, COM, TYP_IRIS, EDI2021, quintileEDI2021`.
Geography stated in sheet `description`: **IRIS au 01.01.2023**.
Higher `EDI2021` = more deprived (negative scores on affluent communes; quintile 1 on those rows).
Deciles are **re-ranked inside metropolitan France** (decile 1 = most deprived). Not IMD, not HP, not SES-WOA.

**Join:** `code_iris` (WFS) = `IRIS` (xlsx), both text with leading zeros.
Expected residual: IGN 49,386 − EDI 48,577 ≈ **809** (plus DOM drop). Unmatched IRIS keep **null** EDI — **not** imputed to 0 (NL trap #11).
Proxy `aequitas_fr_deprivation_proxy` is **not** built: official IRIS F-EDI exists.

## D. Urban–rural

| URL | HTTP | Result |
|-----|------|--------|
| `https://www.insee.fr/fr/information/6439600` | **200** | **La grille de densité 2022** (page also lists 2024 xlsx) |
| `/fr/statistiques/fichier/6439600/grille_densite_7_niveaux_2024.xlsx` | (download in progress / logged at pipeline) | Official 7-level communal density |
| `q=zonage ruralité INSEE` on data.gouv | **200** | 0 |
| Ireland 150/km² / CBS stedelijkheid | — | **not used** |

Rule used: INSEE 7-level density on **commune** (`COM` / `code_insee`), joined to IRIS (many IRIS share a commune — honest, like Ireland HP=ED).
Urban = levels **1–3**; rural = **4–7** (INSEE: grands/centres/ceintures vs petites villes + rural). Documented official cut, not a density copy from another country.

## E. Census cousins (re-checked INSEE, not copied from IE/NL)

| Slot | Search | Result | Action |
|------|--------|--------|--------|
| d2 unemployment | INSEE `base-ic-evol-struct-pop-2018` IRIS | Recensement chômage / actifs if columns present after unzip | **same** if `P18_CHOM*` / actifs join; else omit with the missing name |
| d3 no-car | same table + ménage voiture | **same** if `C18_MEN` voiture-0 exists; else omit |
| d4 elderly | `P18_POP65P` / `P18_POP` | **same** if present |
| d5 income | Filosofi IRIS xlsx URLs below | **same** if file 200; else omit |
| f3 origin | recensement immigrés / étrangers (not “ethnicity”) | **same** as origin cousin if column exists; never call it ethnicity |
| d9a health | INSEE IRIS health domain | **omit** — no free IRIS health-domain score on the files hit |
| d9b employment | recensement activity rate | **same** if present |
| d9c crime | — | **omit** — no free IRIS crime series |
| d9d living environment | — | **omit** — no free IRIS environment domain |
| d9e housing/services | recensement housing if present | **same** if column exists else omit |

Filosofi IRIS URLs **actually tried**:

| URL | HTTP |
|-----|------|
| `https://www.insee.fr/fr/statistiques/7704076` | **TimeoutError** |
| `https://www.insee.fr/fr/statistiques/6692269` | **TimeoutError** |
| `https://www.insee.fr/fr/statistiques/7671844` | **404** |
| `https://www.insee.fr/fr/statistiques/fichier/8229323/BASE_TD_FILO_DISP_IRIS_2021.xlsx` | **500** (curl 56) |
| `https://www.insee.fr/fr/statistiques/fichier/6692218/BASE_TD_FILO_DISP_IRIS_2020.xlsx` | **404** |
| `https://www.insee.fr/fr/statistiques/fichier/6036907/BASE_TD_FILO_DISP_IRIS_2019.xlsx` | **500** |
| `…/fichier/6439600/grille_densite_7_niveaux_2024.xlsx` | **200** 2,683,861 B | CODGEO + DENS, header row 4 |
| `…/fichier/5650720/base-ic-evol-struct-pop-2018_csv.zip` | **200** 19,925,333 B | IRIS `P18_POP`, `P18_POP65P`, `P18_POP_IMM` / `P18_POP_ETR`. **No** chômage, voiture, HLM |
| `https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions-version-simplifiee.geojson` | **200** 225,495 B | 13 metropolitan régions |

Recensement IRIS:

| URL | HTTP | Notes |
|-----|------|-------|
| `https://www.insee.fr/fr/statistiques/5650720` | **200** | Population en 2018 — IRIS *base-ic-evol-struct-pop-2018* |
| `…/fichier/5650720/base-ic-evol-struct-pop-2018_csv.zip` | download logged | Population + structure |

`https://www.insee.fr/fr/information/2017499` → **404**.

## F. Money / carbon

No free ADEME / AOM unit cost downloaded in this recon. Economy = **people-gap + omit-euro sentence**. Illustrative gCO₂/km only if we keep the same honest “illustrative, not ADEME” note as NL — **do not invent BCR**. ADEME factor omitted until a cited free number is on disk.

## Geography / polygons

| URL | HTTP | Notes |
|-----|------|-------|
| `https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions-version-simplifiee.geojson` | download logged | 13 metropolitan régions; **slugs must match GeoJSON `nom`/`code`** (Fryslân trap) |

## What we will omit (one sentence each)

- **d9c** — no free IRIS crime series on INSEE / data.gouv hits.
- **d9d** — no free IRIS living-environment domain.
- **d9a** — no free IRIS health-domain score (F-EDI is a composite, not a health cousin).
- **j2 euro BCR** — no free ADEME/AOM unit cost cited.
- **15/30/45** — not run (`aequitas reach --country france` not in this wave).
- **GTFS-RT / SIRI** — Wave 8, not started.
- **DOM** — out unless both IRIS + GTFS exist for that département.

## Sanity numbers to write after warehouse

- IRIS n vs 49,386 WFS and 48,577 F-EDI
- NAP merged / skipped
- F-EDI join % (do not invent 99%)
- National score bus vs all; Île-de-France ≠ Creuse / rural région
- Gini in [0,1] computed
- Sunday from real calendar join
