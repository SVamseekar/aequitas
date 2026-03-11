# Data Dictionary: Census TS001 Population

**Unit of observation:** One row = one LSOA (England+Wales — filter to E*)  
**Rows:** 33,755  
**Columns:** 6  

## Columns

| Column | Type | Nulls% | Unique | Range/Values | Role |
|--------|------|--------|--------|--------------|------|
| `date` | int64 | 0.0% | 1 | 2e+03 – 2e+03 | **REVIEW** |
| `geography` | str | 0.0% | 33,755 | ['Hartlepool 001A', 'Hartlepool 001B', ' | **USE** |
| `geography code` | str | 0.0% | 33,755 | ['E01011954', 'E01011969', 'E01011970'] | **JOIN KEY** |
| `Residence type: Total; measures: Value` | int64 | 0.0% | 1,956 | 1e+03 – 9.9e+03 | **USE** |
| `Residence type: Lives in a household; measures: Value` | int64 | 0.0% | 1,932 | 5.5e+02 – 3.8e+03 | **IGNORE (household)** |
| `Residence type: Lives in a communal establishment; meas` | int64 | 0.0% | 712 | 0 – 8.8e+03 | **IGNORE (communal)** |

## Traps

- Raw file has 35,672 rows — filter geography code to E* for England-only
- Total population includes communal establishments (prisons, care homes) — use Total not household
- This is ALL ages; NOMIS denominators are age 16+ — never mix for rate calculations
- Population figures are Census night 21 March 2021 — not mid-year estimates