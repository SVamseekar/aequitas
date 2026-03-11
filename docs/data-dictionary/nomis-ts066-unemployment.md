# Data Dictionary: NOMIS TS066 Unemployment

**Unit of observation:** One row = one LSOA (2021 boundaries, England+Wales — filter to E*)  
**Rows:** 33,755  
**Columns:** 34  

## Columns

| Column | Type | Nulls% | Unique | Range/Values | Role |
|--------|------|--------|--------|--------------|------|
| `date` | int64 | 0.0% | 1 | 2e+03 – 2e+03 | **REVIEW** |
| `geography` | str | 0.0% | 33,755 | ['City of London 001A', 'City of London  | **USE** |
| `geography code` | str | 0.0% | 33,755 | ['E01000001', 'E01000002', 'E01000003'] | **JOIN KEY** |
| `Economic activity status: Total: All usual residents ag` | int64 | 0.0% | 1,649 | 7.4e+02 – 9.8e+03 | **USE** |
| `Economic activity status: Economically active (excludin` | int64 | 0.0% | 1,282 | 1.2e+02 – 2.3e+03 | **USE** |
| `Economic activity status: Economically active (excludin` | int64 | 0.0% | 1,261 | 94 – 2.3e+03 | **IGNORE (Full-time)** |
| `Economic activity status: Economically active (excludin` | int64 | 0.0% | 1,128 | 81 – 2.2e+03 | **IGNORE (Full-time)** |
| `Economic activity status: Economically active (excludin` | int64 | 0.0% | 338 | 18 – 6e+02 | **IGNORE (Employee:)** |
| `Economic activity status: Economically active (excludin` | int64 | 0.0% | 990 | 57 – 2e+03 | **IGNORE (Employee:)** |
| `Economic activity status: Economically active (excludin` | int64 | 0.0% | 103 | 0 – 1.2e+02 | **IGNORE (Self-employed)** |
| `Economic activity status: Economically active (excludin` | int64 | 0.0% | 35 | 0 – 54 | **IGNORE (Self-employed)** |
| `Economic activity status: Economically active (excludin` | int64 | 0.0% | 83 | 0 – 90 | **IGNORE (Self-employed)** |
| `Economic activity status: Economically active (excludin` | int64 | 0.0% | 338 | 6 – 4.3e+02 | **IGNORE (Self-employed)** |
| `Economic activity status: Economically active (excludin` | int64 | 0.0% | 173 | 3 – 2.1e+02 | **IGNORE (Self-employed)** |
| `Economic activity status: Economically active (excludin` | int64 | 0.0% | 214 | 1 – 3e+02 | **IGNORE (Self-employed)** |
| `Economic activity status: Economically active (excludin` | int64 | 0.0% | 172 | 0 – 2.9e+02 | **USE** |
| `Economic activity status: Economically active and a ful` | int64 | 0.0% | 427 | 0 – 1.5e+03 | **IGNORE (Full-time)** |
| `Economic activity status: Economically active and a ful` | int64 | 0.0% | 307 | 0 – 8.7e+02 | **IGNORE (full-time student:)** |
| `Economic activity status: Economically active and a ful` | int64 | 0.0% | 288 | 0 – 6.5e+02 | **IGNORE (full-time student:)** |
| `Economic activity status: Economically active and a ful` | int64 | 0.0% | 257 | 0 – 5.9e+02 | **IGNORE (full-time student:)** |
| `Economic activity status: Economically active and a ful` | int64 | 0.0% | 69 | 0 – 2.8e+02 | **IGNORE (full-time student:)** |
| `Economic activity status: Economically active and a ful` | int64 | 0.0% | 15 | 0 – 23 | **IGNORE (full-time student:)** |
| `Economic activity status: Economically active and a ful` | int64 | 0.0% | 12 | 0 – 11 | **IGNORE (full-time student:)** |
| `Economic activity status: Economically active and a ful` | int64 | 0.0% | 11 | 0 – 23 | **IGNORE (full-time student:)** |
| `Economic activity status: Economically active and a ful` | int64 | 0.0% | 58 | 0 – 2.4e+02 | **IGNORE (full-time student:)** |
| `Economic activity status: Economically active and a ful` | int64 | 0.0% | 54 | 0 – 2.2e+02 | **IGNORE (full-time student:)** |
| `Economic activity status: Economically active and a ful` | int64 | 0.0% | 22 | 0 – 38 | **IGNORE (full-time student:)** |
| `Economic activity status: Economically active and a ful` | int64 | 0.0% | 224 | 0 – 7.5e+02 | **IGNORE (full-time student:)** |
| `Economic activity status: Economically inactive` | int64 | 0.0% | 1,192 | 57 – 7.9e+03 | **USE** |
| `Economic activity status: Economically inactive: Retire` | int64 | 0.0% | 859 | 1 – 1.2e+03 | **USE** |
| `Economic activity status: Economically inactive: Studen` | int64 | 0.0% | 765 | 3 – 7.8e+03 | **REVIEW** |
| `Economic activity status: Economically inactive: Lookin` | int64 | 0.0% | 308 | 3 – 4.3e+02 | **USE** |
| `Economic activity status: Economically inactive: Long-t` | int64 | 0.0% | 257 | 0 – 3.7e+02 | **USE** |
| `Economic activity status: Economically inactive: Other` | int64 | 0.0% | 292 | 1 – 2.5e+03 | **REVIEW** |

## Traps

- Raw file has 35,672 rows (England 33,755 + Wales 1,917) — ALWAYS filter geography code LIKE 'E%'
- Unemployment rate = unemployed / economically_active (NOT unemployed / total_pop)
- Full-time students who work are classified separately — excluded from main econ-active denominator
- Long-term sick count is a useful proxy for health deprivation (cross-validate with IMD health score)
- Column names are extremely long — truncate for pipeline use