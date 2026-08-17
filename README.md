# Aequitas

**Public transport briefings against official deprivation — one method, ranks that never leave the country.**

Aequitas joins published timetables to census geography and the national deprivation index, then pre-computes a briefing: a quoteable score, a map, and a fixed set of exhibits. England, Ireland, the Netherlands, and France are live.

Scores are **in-country only**. IMD, Pobal HP, and CBS SES-WOA are never plotted on one axis. Travel times and benefit–cost ratios are not invented.

[![Tests](https://github.com/SVamseekar/aequitas/actions/workflows/test.yml/badge.svg)](https://github.com/SVamseekar/aequitas/actions/workflows/test.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/UI-React_19-087EA4?style=flat-square&logo=react&logoColor=white)](https://react.dev/)
[![DuckDB](https://img.shields.io/badge/warehouse-DuckDB-FFF000?style=flat-square&logo=duckdb&logoColor=black)](https://duckdb.org/)

<p align="center">
  <img src="frontend/public/og-image.png" alt="Aequitas — public transport briefings against official deprivation" width="420" />
</p>

| | |
|---|---|
| Product site | [aequitas.souravamseekar.com](https://aequitas.souravamseekar.com) |
| Application | Local warehouse at [localhost:5173](http://localhost:5173) |

---

## Problem

Transport authorities already publish GTFS, small-area geographies, and a national deprivation measure. What they rarely have is a **reproducible briefing** that answers the same questions in every region.

Aequitas is that briefing. It does not invent travel times, benefit–cost ratios, or a Europe-wide deprivation index.

---

## Coverage

| Country | Network | Deprivation | Geography | Status |
|---|---|---|---|---|
| **England** | BODS GTFS + NaPTAN | IMD 2025 | LSOA 2021 | Live |
| **Ireland** | Transport for Ireland `GTFS_All.zip` | Pobal HP 2022 | CSO Small Areas 2022 (Republic) | Live |
| **Netherlands** | [OVapi](https://gtfs.ovapi.nl/) | CBS SES-WOA 2023 | Buurten 2024 | Live — bus is the default; `?mode=all` includes rail, tram, and metro |
| **France** | NAP GTFS (metropolitan harvest) | F-EDI 2021 | IGN IRIS | Live — 15/30/45 empty until a local r5py run |

### In-country score (0–100)

One function, applied inside each country:

```
100 × (0.40 × people within 400 m
     + 0.25 × evening served
     + 0.20 × weekday quality
     + 0.15 × (1 − |deprivation–service r|))
```

Missing terms are dropped and the remaining weights are renormalised. London has no rural LSOAs, so that filter is empty. Netherlands scores use SES–service correlation, never IMD.

National scores on the current warehouses: **England 80.0**, **Ireland 55.5**, **Netherlands (bus) 69.6**, **France 47.7**.

---

## Product surfaces

| Surface | Purpose |
|---|---|
| **Home** | Map and quoteable score for the active filter |
| **Equity** | Lorenz, Gini, Palma, and deprivation-decile slope — in-country only |
| **Access** | 400 m coverage, deserts, urban–rural gap |
| **Service** | Weekday quality, evening isolation, Sunday deserts |
| **Network** | Single-operator HHI on a 0–10,000 scale |
| **Correlations** | One matrix and one scatter |
| **Economy** | People-gap; official € / TAG unit costs only where a published source exists |
| **Policy** | BSA 2025 (England) · NTA / national policy (Ireland) · concession / OV-wet (Netherlands) · AOM / SPC (France) |
| **Scenarios** | Listed interventions × people × deprivation |
| **Time** | The same network metric across dated snapshots. Census and deprivation stay frozen. |
| **Reach** | Service bands 1–6. 15 / 30 / 45 minute jobs appear only after a local r5py run |
| **Studio** | Walk-to-stop patch on the live filter (not a 45-minute job) |
| **Compare** | Two regions **inside** the same country |

Chat retrieves from a country-specific index where one exists (England, Ireland, France). The France index is local FAISS (not in git). The Netherlands drawer reports that the index is not built. The interface does not invent figures.

---

## Quick start

**Requirements:** Python 3.12+, Node 18+, [`uv`](https://docs.astral.sh/uv/). A pre-built DuckDB warehouse is sufficient to run the dashboard. Warehouse files are **not** stored in git.

```bash
git clone https://github.com/SVamseekar/aequitas.git
cd aequitas
uv sync
cp .env.example .env
./scripts/dev.sh
```

| Resource | Location |
|---|---|
| Landing | http://localhost:5173 |
| England | http://localhost:5173/app/england |
| Ireland | http://localhost:5173/app/ireland |
| Netherlands | http://localhost:5173/app/netherlands |
| France | http://localhost:5173/app/france |
| API health | http://127.0.0.1:8000/api/health |
| Smoke test | `uv run python scripts/smoke_local.py` |

`./scripts/dev.sh` starts Postgres when port 5432 is free, then the API (`:8000`) and Vite (`:5173`). It sets `ENVIRONMENT=development` and `DEV_AUTH_BYPASS=true` so analytics work without Google OAuth.

Rebuild a warehouse from official sources (slow; downloads public files):

```bash
uv run aequitas run            # England
uv run aequitas ireland
uv run aequitas netherlands
uv run aequitas france
```

Optional 15 / 30 / 45 minute layers require Java 17, r5py, and a Geofabrik PBF. If those are absent, Access and Reach stay empty rather than estimated.

---

## Architecture

```
Official GTFS + census + deprivation
        │
        ▼
   Ingest → process → pre-compute
        │
        ▼
   DuckDB (read-only at runtime)
        │
        ├── FastAPI
        │     ├── React application (MapLibre + OSM / CARTO)
        │     └── Optional RAG chat (FAISS + Gemini, per country)
        └── Dated network packs → time-series view
```

Analytics are computed when the warehouse is built. The API is a lookup layer. Narratives are templated from warehouse numbers; weak evidence is omitted, not imputed.

| Layer | Stack |
|---|---|
| Interface | React 19, Vite, TypeScript, Tailwind, MapLibre |
| API | FastAPI, Python 3.12 |
| Warehouse | DuckDB, one file per country |
| Chat | Gemini Flash + FAISS (optional API key) |
| Auth | Postgres + Google OAuth, or a local development bypass |

Copy `.env.example`. The variables that matter for a first run are `AEQUITAS_DB_PATH`, `DATABASE_URL`, `SESSION_SECRET`, and `DEV_AUTH_BYPASS`. Overview pages are public; chat, export, and the application shell require a session (the development bypass satisfies that locally).

---

## Scope

Aequitas **does not**:

- Harmonise IMD, HP, SES-WOA, and F-EDI into a single European index
- Report 15 / 30 / 45 minute access unless r5py has written the parquet
- Publish a benefit–cost ratio without a cited official unit cost
- Host always-on production analytics (the marketing site is static; warehouses run locally)
- Consume live operations feeds (GTFS-RT / SIRI are out of scope for this tree)

---

## Audience

**Transport authorities** — evidence for route reviews and funding.  
**Ministries and regulators** — comparable equity metrics **within** one country.  
**Researchers** — reproducible writers, cited sources, computed Gini (not a locked demonstration number).

To add a country: implement ingest for GTFS, small-area geography, and that country’s official deprivation file. Deprivation ranks must not be labelled IMD unless they are IMD.

---

## Contributing, security, and licence

- [CONTRIBUTING.md](CONTRIBUTING.md) — local setup, `uv` / `./scripts/dev.sh`, test markers, commit style.
- [SECURITY.md](SECURITY.md) — private reports to martisoura@gmail.com. Do not file public 0-days.
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [LICENSE](LICENSE) — all rights reserved. Write before adapting the product for an authority or research programme.

Support: [GitHub Issues](https://github.com/SVamseekar/aequitas/issues). Method work lives on [issue #17](https://github.com/SVamseekar/aequitas/issues/17).

## Contact

**Marti Soura Vamseekar** · [martisoura@gmail.com](mailto:martisoura@gmail.com) · [souravamseekar.com](https://souravamseekar.com)
