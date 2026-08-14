# Code Gotchas and Data Quality Traps

Common implementation traps, API quirks, and data-quality gotchas in the Aequitas platform.

**Multi-country:** Waves 5–6 are stamped Done (see `docs/CURRENT_STATE.md` §11). Ireland’s closed mistakes (seed marked live, England nouns, GB map after MapLibre abort, England/BODS export, unknown pack falling back, ticker “England is live”, factory bars, `kpi_tiles` as a “chart”, Insight one-liners, `/economic` empty door) must not be repeated for the Netherlands or France. Full list: [country-sections.md](country-sections.md) — *Ireland mistakes — do not repeat (NL / FR)*.

---

## 1. Data Ingestion & API Gotchas

### NumPy 2.x API Changes
- **Gotcha:** `np.trapz` has been removed in NumPy 2.x.
- **Trap Avoidance:** Always use `np.trapezoid`. To maintain compatibility, use a check like `getattr(np, 'trapezoid', getattr(np, 'trapz', None))` or standard `hasattr` checks.

### GIAS School File Encoding
- **Gotcha:** GIAS (Get Information About Schools) data is encoded in `latin-1` instead of `utf-8`.
- **Trap Avoidance:** Set `encoding='latin-1'` when reading the csv/parquet GIAS files.

### NHS ODS API Pagination
- **Gotcha:** The NHS ODS API pagination offset starts at 1 (not 0).
- **Trap Avoidance:** Always read the `Next-Page` header in responses to confirm if another page of records exists.

### NOMIS BRES Data Suppression
- **Gotcha:** NOMIS BRES (Business Register and Employment Survey) data is suppressed at the LSOA level.
- **Trap Avoidance:** Use the MSOA level instead (`TYPE297`), specifying `date=2023` and `employment_status=1` to query total employment.

---

## 2. Database & Search Gotchas

### DuckDB Connection Locking
- **Gotcha:** DuckDB allows multiple read connections but only one write connection.
- **Trap Avoidance:** The analytics pipeline must have exclusive access to DuckDB when building the database. The FastAPI backend must open the warehouse file in read-only mode (`read_only=True`) to avoid lock-acquisition failures during runtime requests.

### FAISS Character-to-Token Ratios
- **Gotcha:** The RAG index builder uses character proxy metrics (500 characters ≈ 125 tokens) for text chunking.
- **Trap Avoidance:** Keep chunk sizes aligned to character counts rather than assuming strict token mapping to prevent token overflow in Gemini calls.
