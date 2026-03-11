---
paths:
  - "src/aequitas/intelligence/**"
  - "src/aequitas/warehouse/**"
---

# InsightEngine Rules

- InsightEngine is deterministic — Jinja2 templates + evidence-gated rules only, NO LLM calls here
- A rule must not fire unless its evidence threshold is met — suppress > mislead, always
- TAG 2024 constants live in `core/constants.py` only — never hardcode BCR values or time values inline
- Every metric that appears in a narrative must be traceable to a specific column in a specific Parquet file
- No hardcoded narrative text — 0 lines of hardcoded strings in output
- Narrative tone: consulting-grade, quantified, no qualitative vagueness
- BCR calculations must follow HM Treasury Green Book methodology exactly
- All 30 filter combinations (10 regions × 3 area types) must produce valid, non-null results
