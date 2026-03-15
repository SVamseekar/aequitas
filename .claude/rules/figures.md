---
paths:
  - "notebooks/**/*.ipynb"
  - "notebooks/**/*.py"
  - "src/aequitas/**/*.py"
  - "docs/**/*.md"
---

# Figures Registry Rule — Non-Negotiable

Every specific number, rate, cost, correlation, or statistical claim used anywhere in this
project must have an entry in `docs/figures-registry.md`.

## Before using any figure

1. Check `docs/figures-registry.md` for the figure
2. Apply the decision:

| Status | Decision |
|--------|----------|
| ✅ Confirmed | Use it |
| ⚠️ Stale | Verify against the listed correct source → update registry to ✅ Confirmed → use it. If cannot verify, do not use — flag to user. |
| ❌ Unverified | Find a strong source → update registry to ✅ Confirmed → use it. If no strong source exists, do not use — flag to user. |
| Not in registry (new figure) | Strong source exists → add to registry as ✅ Confirmed → use it. No strong source → do not use — flag to user. |

## What counts as a strong source
- Our own Phase 0 audit notebook output
- ONS dataset (Census, NOMIS, IMD)
- DfT publication (TAG Databook, WebTAG, TSGB)
- HM Treasury publication (Green Book)
- DESNZ publication (GHG conversion factors)
- NHS ODS / GIAS official data extracts
- Peer-reviewed transport economics literature

## What does NOT count as a strong source
- Old project (uk_bus_analytics) docs or code
- Blog posts, news articles, estimates
- Remembered or approximate values
- "It was ~X in the old project"

## When a notebook produces a new figure
Add it to the registry appendix (Category matching its type) before the session ends.
Format: ID | Figure | Value | ✅ Confirmed | notebook_name.ipynb | brief note
