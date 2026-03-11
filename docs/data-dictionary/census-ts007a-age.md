# Data Dictionary: Census TS007a Age

**Unit of observation:** One row = one LSOA (England+Wales — filter to E*)  
**Rows:** 33,755  
**Columns:** 22  

## Columns

| Column | Type | Nulls% | Unique | Range/Values | Role |
|--------|------|--------|--------|--------------|------|
| `date` | int64 | 0.0% | 1 | 2e+03 – 2e+03 | **IGNORE (date)** |
| `geography` | str | 0.0% | 33,755 | ['City of London 001A', 'City of London  | **USE** |
| `geography code` | str | 0.0% | 33,755 | ['E01000001', 'E01000002', 'E01000003'] | **JOIN KEY** |
| `Age: Total` | int64 | 0.0% | 1,955 | 1e+03 – 9.9e+03 | **USE** |
| `Age: Aged 4 years and under` | int64 | 0.0% | 310 | 2 – 5.5e+02 | **USE** |
| `Age: Aged 5 to 9 years` | int64 | 0.0% | 301 | 2 – 6.2e+02 | **USE** |
| `Age: Aged 10 to 14 years` | int64 | 0.0% | 319 | 0 – 4.8e+02 | **USE** |
| `Age: Aged 15 to 19 years` | int64 | 0.0% | 542 | 2 – 3.8e+03 | **USE** |
| `Age: Aged 20 to 24 years` | int64 | 0.0% | 760 | 16 – 4.2e+03 | **USE** |
| `Age: Aged 25 to 29 years` | int64 | 0.0% | 480 | 13 – 1.2e+03 | **USE** |
| `Age: Aged 30 to 34 years` | int64 | 0.0% | 402 | 10 – 6.3e+02 | **USE** |
| `Age: Aged 35 to 39 years` | int64 | 0.0% | 320 | 17 – 4.9e+02 | **USE** |
| `Age: Aged 40 to 44 years` | int64 | 0.0% | 273 | 8 – 4.2e+02 | **USE** |
| `Age: Aged 45 to 49 years` | int64 | 0.0% | 256 | 10 – 3.3e+02 | **USE** |
| `Age: Aged 50 to 54 years` | int64 | 0.0% | 265 | 0 – 3.1e+02 | **USE** |
| `Age: Aged 55 to 59 years` | int64 | 0.0% | 268 | 0 – 3e+02 | **USE** |
| `Age: Aged 60 to 64 years` | int64 | 0.0% | 254 | 0 – 2.8e+02 | **USE** |
| `Age: Aged 65 to 69 years` | int64 | 0.0% | 243 | 0 – 2.7e+02 | **USE** |
| `Age: Aged 70 to 74 years` | int64 | 0.0% | 277 | 0 – 3.6e+02 | **USE** |
| `Age: Aged 75 to 79 years` | int64 | 0.0% | 227 | 0 – 3e+02 | **USE** |
| `Age: Aged 80 to 84 years` | int64 | 0.0% | 174 | 0 – 2.2e+02 | **USE** |
| `Age: Aged 85 years and over` | int64 | 0.0% | 218 | 0 – 3.7e+02 | **USE** |

## Traps

- Raw file has 35,672 rows (E+W) — filter to E*
- 'Age: Aged 85 years and over' is unbounded — cannot distinguish 85 from 100
- Elderly 65+ = sum of columns containing 65, 70, 75, 80, 85 in column name
- Age bands are 5-year intervals — cannot subdivide further
- Total should equal Census TS001 total within ±5 (rounding differences)