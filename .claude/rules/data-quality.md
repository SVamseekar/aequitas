---
paths:
  - "src/aequitas/ingestion/**"
  - "src/aequitas/processing/**"
  - "src/aequitas/validation/**"
  - "src/aequitas/core/models.py"
---

# Data Quality Rules — Non-Negotiable

## Entity Counting (critical)
- A BusStop = one physical location, identified by ATCO code, counted ONCE
- A Route = one named service, identified by route_id, counted ONCE regardless of regions or journey patterns
- NaPTAN: filter StopType to BCT/BCS/BCE only — rail/tram/ferry/taxi stops must be excluded
- BODS: count routes not journey patterns — one route has many daily patterns
- Cross-region deduplication is mandatory — same route in 2 regional feeds = 1 route

## Known Data Traps
- IMD 2019 has 32,844 LSOAs; Census 2021 has 33,755 — ~900 boundary mismatch, must document handling
- NOMIS unemployment is MSOA-level only — requires distribution to LSOA with lookup table
- NaPTAN covers all UK transport modes — must filter to England bus stops only
- ONS Census LSOA population sum must equal official regional total — validate this explicitly

## Validation Gates
- Every ingestion step must write a validation report before the next step starts
- Match rates for all spatial joins must be logged (stop→LSOA, LSOA→demographics)
- Any match rate below 95% must raise a warning and halt unless explicitly overridden
- Ground truth counts (established in data audit notebook) must be checked at pipeline end
