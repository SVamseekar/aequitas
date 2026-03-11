# Data Dictionary: Census TS045 Car Ownership

**Unit of observation:** One row = one LSOA (England+Wales — filter to E*)  
**Rows:** 33,755  
**Columns:** 8  

## Columns

| Column | Type | Nulls% | Unique | Range/Values | Role |
|--------|------|--------|--------|--------------|------|
| `date` | int64 | 0.0% | 1 | 2e+03 – 2e+03 | **IGNORE (date)** |
| `geography` | str | 0.0% | 33,755 | ['City of London 001A', 'City of London  | **USE** |
| `geography code` | str | 0.0% | 33,755 | ['E01000001', 'E01000002', 'E01000003'] | **JOIN KEY** |
| `Number of cars or vans: Total: All households` | int64 | 0.0% | 820 | 4e+02 – 1.5e+03 | **USE** |
| `Number of cars or vans: No cars or vans in household` | int64 | 0.0% | 761 | 2 – 1e+03 | **USE** |
| `Number of cars or vans: 1 car or van in household` | int64 | 0.0% | 530 | 49 – 6.9e+02 | **USE** |
| `Number of cars or vans: 2 cars or vans in household` | int64 | 0.0% | 508 | 0 – 6.2e+02 | **IGNORE (2 cars)** |
| `Number of cars or vans: 3 or more cars or vans in house` | int64 | 0.0% | 277 | 0 – 3.1e+02 | **IGNORE (3 or more)** |

## Traps

- Raw file has 35,672 rows (E+W) — filter to E*
- HOUSEHOLD-level, NOT person-level — do not divide by population
- High no-car % = wealthy city centre (London) OR poor deprived area — NOT a simple poverty signal
- '3 or more' is unbounded — no distinction between 3 and 10 cars
- Includes vans — some households are commercial, skews rural LSOAs
- No-car rate = no_cars / total_households (not per person)