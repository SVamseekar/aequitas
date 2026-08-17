# Contributing

Thank you for taking an interest in Aequitas. This repository is the source for a four-country briefing product. Viewing the source does not grant a licence to reuse the product; see [LICENSE](LICENSE).

## Support and method work

- Bugs and small enhancements: [GitHub Issues](https://github.com/SVamseekar/aequitas/issues).
- Method / country-pipeline work is tracked on [issue #17](https://github.com/SVamseekar/aequitas/issues/17).
- Security reports: see [SECURITY.md](SECURITY.md). Do not open a public issue for an unpatched vulnerability.

There is no public chat server. Email the maintainer if an issue is not the right channel.

## Local setup

Requirements: Python 3.12+, Node 18+, [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/SVamseekar/aequitas.git
cd aequitas
uv sync
cp .env.example .env
./scripts/dev.sh
```

`./scripts/dev.sh` starts Postgres when port 5432 is free, then the API (`:8000`) and Vite (`:5173`). It sets `ENVIRONMENT=development` and `DEV_AUTH_BYPASS=true`.

A pre-built DuckDB warehouse is enough to run the dashboard. Warehouse files are not stored in git. Do not commit them.

## Tests

```bash
# Backend — skip warehouse-backed tests (full pytest without this marker can hang)
uv run pytest tests/ -q -m "not requires_data"

# Frontend
cd frontend && npx vitest run
```

CI uses the same split (see `.github/workflows/test.yml`). Do not enable a full unmarked pytest run in pull requests.

## Commits and pull requests

Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).

Open a pull request against `main`. Fill in `.github/PULL_REQUEST_TEMPLATE.md`.

## Never commit

- DuckDB warehouses (`*.duckdb`, `*.duckdb.wal`)
- FAISS indices and embedding binaries
- Ops rollups (`data/ops/`)
- Country harvest directories (`data/france/`, `data/ireland/`)
- OSM extracts (`*.pbf`) and large GTFS zip archives
- `.env` and API keys
- Local QA dumps (`qa-visual/`, `frontend/scripts/qa-*.mjs`)

Allowed small artefacts include `data/packs/**/metrics.json` and `frontend/public/boundaries/*.geojson`.

## Honesty

Do not invent 15 / 30 / 45 minute access figures, benefit–cost ratios, or a Europe-wide deprivation index. Missing evidence stays empty.
