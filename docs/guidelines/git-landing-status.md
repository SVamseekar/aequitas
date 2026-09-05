# Git landing status

Date: 2026-08-17
Author: landing agent
Intent: one PR — France briefing from NAP GTFS, IGN IRIS, and F-EDI
Branch: `feat/france-nap-fedi-iris`
Base: `origin/main` `5995148` (PR #9)
PR: https://github.com/SVamseekar/aequitas/pull/10

## Verdict
OPEN — do not merge from this session. Frontend green after HomePage test update.
Backend first failed on `test_nl_fr_pack_404` (France now 200). Test renamed and
autosquashed into commit 1. CI re-running.

## Commits
1. `feat(france): add NAP harvest, IGN IRIS, and F-EDI warehouse writers`
2. `feat(frontend): France briefing, F-EDI nouns, and landing Live card`

## Not staged
DuckDB, `data/france/`, `data/ireland/`, qa scripts, rebuild_nl, this file,
france-sources.md, node_modules.

This file is unstaged on purpose.
