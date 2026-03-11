# Data Dictionary: NaPTAN Stops

**Unit of observation:** One row = one physical bus stop location  
**Rows:** 434,248  
**Columns:** 43  

## Columns

| Column | Type | Nulls% | Unique | Range/Values | Role |
|--------|------|--------|--------|--------------|------|
| `ATCOCode` | str | 0.0% | 434,248 | ['0100BRP90317', '0100BRP90318', '0100BR | **JOIN KEY** |
| `NaptanCode` | str | 6.0% | 408,193 | ['ltnadajd', 'dloajmtj', 'sktgwpm'] | **JOIN KEY** |
| `PlateCode` | str | 85.5% | 62,133 | ['2', '3', '10'] | **REVIEW** |
| `CleardownCode` | float64 | 100.0% | 0 | [] | **IGNORE (CleardownCode)** |
| `CommonName` | str | 0.0% | 168,022 | ['Post Office', 'Bus Station', 'Church'] | **USE** |
| `CommonNameLang` | float64 | 100.0% | 0 | [] | **IGNORE (Lang)** |
| `ShortCommonName` | str | 78.4% | 44,078 | ['Rd End', 'Township', 'Post Office'] | **IGNORE (ShortCommon)** |
| `ShortCommonNameLang` | float64 | 100.0% | 0 | [] | **IGNORE (Lang)** |
| `Landmark` | str | 43.0% | 103,442 | ['Unknown', '*', 'Landmark not known'] | **REVIEW** |
| `LandmarkLang` | float64 | 100.0% | 0 | [] | **IGNORE (Lang)** |
| `Street` | str | 5.6% | 63,499 | ['High Street', 'Main Street', 'Station  | **REVIEW** |
| `StreetLang` | float64 | 100.0% | 0 | [] | **IGNORE (Lang)** |
| `Crossing` | float64 | 100.0% | 0 | [] | **IGNORE (Crossing)** |
| `CrossingLang` | float64 | 100.0% | 0 | [] | **IGNORE (Lang)** |
| `Indicator` | str | 5.5% | 14,130 | ['opp', 'adj', 'at'] | **USE** |
| `IndicatorLang` | float64 | 100.0% | 0 | [] | **IGNORE (Lang)** |
| `Bearing` | str | 5.4% | 8 | ['N', 'S', 'E'] | **USE** |
| `NptgLocalityCode` | str | 0.0% | 34,079 | ['E0057189', 'E0057571', 'E0057786'] | **REVIEW** |
| `LocalityName` | str | 0.0% | 29,394 | ['Leicester', 'Norwich', 'Manchester Cit | **USE** |
| `ParentLocalityName` | str | 56.3% | 1,872 | ['London', 'Birmingham', 'Sheffield'] | **REVIEW** |
| `GrandParentLocalityName` | float64 | 100.0% | 0 | [] | **IGNORE (GrandParent)** |
| `Town` | str | 63.8% | 6,221 | ['BIRMINGHAM', 'Sheffield', 'Doncaster'] | **REVIEW** |
| `TownLang` | str | 96.5% | 1 | ['EN'] | **IGNORE (Lang)** |
| `Suburb` | str | 83.7% | 5,949 | ['-', 'Call Connect', 'Town Centre'] | **REVIEW** |
| `SuburbLang` | str | 97.3% | 1 | ['EN'] | **IGNORE (Lang)** |
| `LocalityCentre` | str | 1.5% | 4 | ['false', '0', '1'] | **REVIEW** |
| `GridType` | str | 3.6% | 1 | ['UKOS'] | **REVIEW** |
| `Easting` | int64 | 0.0% | 251,396 | 0 – 7.6e+05 | **USE** |
| `Northing` | int64 | 0.0% | 288,226 | 0 – 1.2e+06 | **USE** |
| `Longitude` | float64 | 12.1% | 361,427 | -7.6 – 1.8 | **USE** |
| `Latitude` | float64 | 12.1% | 343,470 | 50 – 61 | **USE** |
| `StopType` | str | 0.0% | 18 | ['BCT', 'BCS', 'RSE'] | **USE** |
| `BusStopType` | str | 4.2% | 4 | ['MKD', 'CUS', 'HAR'] | **USE** |
| `TimingStatus` | str | 3.5% | 5 | ['OTH', 'TIP', 'PPT'] | **USE** |
| `DefaultWaitTime` | float64 | 100.0% | 0 | [] | **IGNORE (DefaultWaitTime)** |
| `Notes` | float64 | 100.0% | 0 | [] | **IGNORE (Notes)** |
| `NotesLang` | float64 | 100.0% | 0 | [] | **IGNORE (Lang)** |
| `AdministrativeAreaCode` | int64 | 0.0% | 148 | 1 – 1.5e+02 | **USE** |
| `CreationDateTime` | str | 0.0% | 50,857 | ['1970-01-01T00:00:00', '2000-01-01T00:0 | **USE** |
| `ModificationDateTime` | str | 0.1% | 244,243 | ['2025-05-01T00:00:00', '2023-12-12T15:0 | **USE** |
| `RevisionNumber` | float64 | 2.3% | 299 | 0 – 1.1e+03 | **REVIEW** |
| `Modification` | str | 8.1% | 3 | ['revise', 'new', 'delete'] | **REVIEW** |
| `Status` | str | 0.0% | 3 | ['active', 'inactive', 'pending'] | **USE** |

## Traps

- StopType must be filtered to BCT/BCS/BCE for bus stops only (18 stop types exist)
- Status must be filtered to 'active' (inactive=45,840, pending=1)
- ATCO prefix 0xx-4xx = England only; 5xx=Wales, 6xx=Scotland
- 52,449 rows have null Longitude/Latitude — use Easting/Northing as fallback
- NaptanCode → BODS stop_code join (NOT ATCOCode → stop_id)
- Multiple stops share CommonName (e.g. 'Temple Meads Stn' = 7 different stops)
- BusStopType null for non-bus stop types — filter StopType first