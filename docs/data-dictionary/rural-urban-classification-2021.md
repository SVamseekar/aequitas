# Data Dictionary: Rural Urban Classification 2021

**Unit of observation:** One row = one LSOA (England+Wales — filter to E*)  
**Rows:** 33,755  
**Columns:** 7  

## Columns

| Column | Type | Nulls% | Unique | Range/Values | Role |
|--------|------|--------|--------|--------------|------|
| `LSOA21CD` | str | 0.0% | 33,755 | ['E01000001', 'E01000002', 'E01000003'] | **JOIN KEY** |
| `LSOA21NM` | str | 0.0% | 33,755 | ['City of London 001A', 'City of London  | **IGNORE (LSOA21NM)** |
| `LSOA21NMW` | str | 100.0% | 0 | [] | **IGNORE (NMW)** |
| `RUC21CD` | str | 0.0% | 6 | ['UN1', 'RLN1', 'UF1'] | **USE** |
| `RUC21NM` | str | 0.0% | 6 | ['Urban: Nearer to a major town or city' | **USE** |
| `Urban_rural_flag` | str | 0.0% | 2 | ['Urban', 'Rural'] | **USE** |
| `ObjectId` | int64 | 0.0% | 33,755 | 1 – 3.4e+04 | **REVIEW** |

## Traps

- Urban_rural_flag is binary (Urban/Rural) — use RUC21CD for 6-category analysis
- 6 categories: UN1 urban-core, UF1 urban-fringe, RSN1 rural-small-town, RLN1 rural-less-sparse, RSF1 rural-sparse, RLF1 rural-very-remote
- Classification is distance-based (proximity to nearest major town), NOT density-based
- RSN1 (Small rural towns near cities) is classified Rural despite urban proximity
- LSOA21NMW (Welsh names) is 94.6% null — ignore entirely