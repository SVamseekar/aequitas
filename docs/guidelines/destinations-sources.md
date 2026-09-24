# Destinations — source log (issue #21)

Official jobs / GP / school points for 15/30/45 and 400 m facility access.
Ranks stay inside the country. **Do not** copy BRES / NHS ODS / GIAS codes onto
Ireland, the Netherlands, or France.

Layout (gitignored under `data/processed/`):

```
data/processed/{country}/destinations_{jobs,gp,school}.parquet
```

England may still read the legacy flat `data/processed/destinations_{type}.parquet`
if the country-keyed file is missing. IE/NL/FR never fall through to that file.

CLI: `uv run aequitas destinations --country {england,ireland,netherlands,france}`

API: `GET /api/destinations?country=`

Schema: `dest_id`, `dest_type`, `lat`, `lon`, plus optional `name`, `area_id`,
`weight`, `source`. LSOA columns are **not** required on IE/NL/FR.

A 404 / missing extract / non-point catalog is an **omit** (one sentence, no
invented rows). Status **0** is a TCP failure (connection refused), not a
portal 404.

## This checkout (2026-09-12, measured)

Backend on `127.0.0.1:8000` (no auth bypass). Scores unchanged: **80.0 / 55.5 /
69.6 / 47.7**. `/api/reach?country=france` stays empty. France/Ireland/NL
`/api/destinations` do **not** report England row counts.

### Written dest parquets

| Country | jobs | gp | school | Source |
|---------|-----:|---:|-------:|--------|
| England | **33,755** | **12,059** | **3,336** | Phase 0 audit re-export (BRES proxy × ONS PWC; NHS ODS GP; GIAS secondary) |
| Ireland | omit | omit | omit | CKAN search 200 was visit cubes, not practice points |
| Netherlands | omit | omit | omit | CBS ODataApi TCP refused this session |
| France | omit | omit | omit | data.gouv TCP refused; INSEE `BPE23.zip` **500** |

### Live HTTP (this session)

| Country | URL | HTTP | Bytes | Notes |
|---------|-----|-----:|------:|-------|
| England | `https://files.digital.nhs.uk/assets/ods/current/epraccur.zip` | **403** then **0** | 0 | HEAD 403 (curl); later CLI TCP refused. Re-export used audit parquet instead |
| England | `https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/edubasealldata.csv` | **0** | 0 | TCP refused. Do not invent a dated GIAS path |
| Ireland | `https://data.gov.ie/api/3/action/package_search?q=general%20practitioner` | **200** | **37,040** | 6 packages, all CSO PxStat *GP visit / medical card* cubes. **No lat/lon**. Omitted |
| Ireland | `…package_search?q=post-primary%20schools` | **0** | 0 | TCP refused |
| Ireland | `…package_search?q=primary%20schools` | **0** | 0 | TCP refused |
| Ireland | `…package_search?q=POWSCAR` | **0** | 0 | TCP refused |
| Netherlands | `https://opendata.cbs.nl/ODataApi/odata/84718NED` | **0** | 0 | TCP refused |
| Netherlands | `https://opendata.cbs.nl/ODataApi/odata/80305NED` | **0** | 0 | TCP refused |
| Netherlands | `https://opendata.cbs.nl/ODataApi/odata/85984NED` | **0** | 0 | TCP refused (ODataApi). Wave 7 warehouse harvest of this table is a **different day** |
| Netherlands | `https://opendata.cbs.nl/ODataFeed/odata/85984NED/TypedDataSet?$top=1` | **404** | 0 | curl HEAD. Do not invent another table id |
| France | `https://www.data.gouv.fr/api/1/datasets/?q=base%20permanente%20des%20equipements` | **200** then **0** | 0 | HEAD 200 once; CLI later TCP refused |
| France | `https://www.data.gouv.fr/api/1/datasets/base-permanente-des-equipements-1/` | **0** | 0 | TCP refused |
| France | `https://www.data.gouv.fr/api/1/datasets/base-permanente-des-equipements-geographique-bpe/` | **0** | 0 | TCP refused |
| France | `https://www.insee.fr/fr/statistiques/8217525` | **200** | — | HTML page HEAD |
| France | `https://www.insee.fr/fr/statistiques/fichier/8217525/BPE23.zip` | **500** | **44,105** | Portal error. Omit. Do not invent a second zip name |

PxStat cube URLs from the Ireland GP catalog are **not** followed (survey
aggregates, not HSE practice coordinates).

## On-disk warehouse tables (not dest points)

| Table | n | Employment-like columns | Dest action |
|-------|--:|-------------------------|-------------|
| `processed/ireland/sa_table.parquet` | 18,919 | none | jobs omit |
| `processed/netherlands/buurt_table.parquet` | 13,827 | `labour_part` (rate), `ww` (benefit count) | jobs omit — not a workplace count |
| `processed/france/iris_table.parquet` | 48,522 | none | jobs omit |

Do not treat population or labour participation as jobs.

Local drop-in (any country): put a CSV/Parquet with lat/lon in
`data/raw/{country}/destinations/` named with `jobs`, `gp`, or `school`.

## What we will not claim

- England dests on `/api/reach?country=ireland|netherlands|france`
- Ireland GP dests from CSO visit cubes
- OSM Overpass as “NHS” / “HSE” / “BPE”
- Invented 15/30/45 counts (#12 still needs r5py + PBF + country dest files)
- Europe-wide jobs Gini
- Status 0 as a portal 404
