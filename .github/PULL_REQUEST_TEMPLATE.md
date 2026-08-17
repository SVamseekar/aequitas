## Summary

<!-- What changed and why. Conventional Commits subject in the PR title. -->

## How to test

- [ ] `uv run pytest tests/ -q -m "not requires_data"`
- [ ] `cd frontend && npx vitest run`
- [ ] (If UI) exercised the changed route in the browser

## Checklist

- [ ] Did **not** stage `*.duckdb`, `*.duckdb.wal`, FAISS binaries, or `data/ops/`
- [ ] Did **not** stage `data/france/`, `data/ireland/`, `qa-visual/`, `.env`, `*.pbf`, or GTFS zips
- [ ] Did **not** invent 15 / 30 / 45 figures or a Europe-wide deprivation index
- [ ] Tests keep the `not requires_data` split (full unmarked pytest is known to hang)
