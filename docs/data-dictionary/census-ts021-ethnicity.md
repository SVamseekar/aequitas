# Data Dictionary: Census TS021 Ethnicity

**Unit of observation:** One row = one LSOA (England+Wales — filter to E*)  
**Rows:** 33,755  
**Columns:** 28  

## Columns

| Column | Type | Nulls% | Unique | Range/Values | Role |
|--------|------|--------|--------|--------------|------|
| `date` | int64 | 0.0% | 1 | 2e+03 – 2e+03 | **IGNORE (date)** |
| `geography` | str | 0.0% | 33,755 | ['City of London 001A', 'City of London  | **USE** |
| `geography code` | str | 0.0% | 33,755 | ['E01000001', 'E01000002', 'E01000003'] | **JOIN KEY** |
| `Ethnic group: Total: All usual residents` | int64 | 0.0% | 1,963 | 1e+03 – 9.9e+03 | **USE** |
| `Ethnic group: Asian, Asian British or Asian Welsh` | int64 | 0.0% | 1,559 | 0 – 2.6e+03 | **USE** |
| `Ethnic group: Asian, Asian British or Asian Welsh: Bang` | int64 | 0.0% | 597 | 0 – 2.2e+03 | **IGNORE (: Bangladeshi)** |
| `Ethnic group: Asian, Asian British or Asian Welsh: Chin` | int64 | 0.0% | 275 | 0 – 8.6e+02 | **IGNORE (: Chinese)** |
| `Ethnic group: Asian, Asian British or Asian Welsh: Indi` | int64 | 0.0% | 860 | 0 – 2.4e+03 | **IGNORE (: Indian)** |
| `Ethnic group: Asian, Asian British or Asian Welsh: Paki` | int64 | 0.0% | 964 | 0 – 2.2e+03 | **IGNORE (: Pakistani)** |
| `Ethnic group: Asian, Asian British or Asian Welsh: Othe` | int64 | 0.0% | 372 | 0 – 6.5e+02 | **REVIEW** |
| `Ethnic group: Black, Black British, Black Welsh, Caribb` | int64 | 0.0% | 847 | 0 – 1.6e+03 | **USE** |
| `Ethnic group: Black, Black British, Black Welsh, Caribb` | int64 | 0.0% | 609 | 0 – 1.3e+03 | **IGNORE (: African)** |
| `Ethnic group: Black, Black British, Black Welsh, Caribb` | int64 | 0.0% | 338 | 0 – 6e+02 | **IGNORE (: Caribbean)** |
| `Ethnic group: Black, Black British, Black Welsh, Caribb` | int64 | 0.0% | 162 | 0 – 3.1e+02 | **REVIEW** |
| `Ethnic group: Mixed or Multiple ethnic groups` | int64 | 0.0% | 271 | 0 – 6.6e+02 | **USE** |
| `Ethnic group: Mixed or Multiple ethnic groups: White an` | int64 | 0.0% | 112 | 0 – 3.5e+02 | **REVIEW** |
| `Ethnic group: Mixed or Multiple ethnic groups: White an` | int64 | 0.0% | 84 | 0 – 1.9e+02 | **REVIEW** |
| `Ethnic group: Mixed or Multiple ethnic groups: White an` | int64 | 0.0% | 145 | 0 – 2.6e+02 | **REVIEW** |
| `Ethnic group: Mixed or Multiple ethnic groups: Other Mi` | int64 | 0.0% | 120 | 0 – 2.5e+02 | **REVIEW** |
| `Ethnic group: White` | int64 | 0.0% | 2,564 | 15 – 7.1e+03 | **USE** |
| `Ethnic group: White: English, Welsh, Scottish, Northern` | int64 | 0.0% | 2,531 | 3 – 5.2e+03 | **IGNORE (English, Welsh)** |
| `Ethnic group: White: Irish` | int64 | 0.0% | 125 | 0 – 1.8e+02 | **IGNORE (Irish)** |
| `Ethnic group: White: Gypsy or Irish Traveller` | int64 | 0.0% | 84 | 0 – 2.5e+02 | **IGNORE (Irish)** |
| `Ethnic group: White: Roma` | int64 | 0.0% | 98 | 0 – 5.1e+02 | **REVIEW** |
| `Ethnic group: White: Other White` | int64 | 0.0% | 671 | 0 – 1.8e+03 | **REVIEW** |
| `Ethnic group: Other ethnic group` | int64 | 0.0% | 404 | 0 – 9.3e+02 | **USE** |
| `Ethnic group: Other ethnic group: Arab` | int64 | 0.0% | 257 | 0 – 5.8e+02 | **REVIEW** |
| `Ethnic group: Other ethnic group: Any other ethnic grou` | int64 | 0.0% | 314 | 0 – 4.9e+02 | **REVIEW** |

## Traps

- Raw file has 35,672 rows (E+W) — filter to E*
- Hierarchy: group totals should >= sum of subcategories
- 2021 added Roma explicitly — NOT comparable to 2011 Census ethnicity data
- 'White: Other White' is a residual catch-all (Polish, Italian, etc.) — not homogeneous
- Census 2021 allowed multiple-tick for mixed groups — some double-counting possible at sub-category level
- Non-white % = (Total - White) / Total