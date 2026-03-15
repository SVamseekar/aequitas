---
name: data-audit
description: Run or continue the Aequitas data audit — profiles raw government data sources, establishes ground truth counts, and locks in entity definitions before any pipeline code is written.
disable-model-invocation: true
---

# Data Audit Skill

This skill guides the data audit process for Aequitas. The audit MUST complete before any pipeline code is written.

## What the audit establishes

For each source (NaPTAN, BODS, Census, IMD, NOMIS, GeoJSON boundaries):
- Exact row counts
- Column names (verbatim from file headers)
- Unique identifier counts
- Null rates on key columns
- Geographic scope confirmation
- Join key identification and match rates

## Ground truth numbers to lock in

```
NaPTAN:
  Total rows in Stops.csv: ___
  Rows where StopType is BCT/BCS/BCE: ___
  Unique ATCO codes after bus-type filter: ___
  Stops within England bounds (lat 49.9-55.8, lon -6.4 to 2.0): ___

BODS (all 9 regional feeds combined):
  Total route records across all regions: ___
  Unique route_ids: ___
  Routes appearing in 2+ regions (cross-region duplication): ___
  Unique routes after deduplication: ___

Census 2021:
  Total LSOAs in population file: ___
  Sum of all LSOA populations: ___
  Sum cross-checked against ONS England total (~56.3M): ___

IMD 2025:
  Total LSOAs: 33,755 ✓ LOCKED
  LSOAs with no match in Census 2021 boundaries: 0 ✓ LOCKED (uses 2021 boundaries)

Spatial joins:
  Bus stops successfully assigned to an LSOA: ___  (target: >95%)
  LSOAs with at least one bus stop: ___
  LSOAs with zero bus stops (coverage deserts): ___
  Population in LSOAs with zero bus stops: ___
```

## Notebook location
`notebooks/01_data_audit.ipynb`

## Steps
1. If notebook doesn't exist yet, create it
2. For the requested source ($ARGUMENTS), profile the raw file
3. Fill in the ground truth numbers above
4. Document any anomalies or data traps found
5. Update `memory/architecture.md` with confirmed counts

If $ARGUMENTS is empty, start with NaPTAN (highest priority — wrong stop count breaks everything).
