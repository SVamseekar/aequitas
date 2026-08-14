# Country section catalogue

Law for Waves 5 / 7 / 9. **Ireland, the Netherlands, and France use the same
plan.** Ten product doors stay. Inner England questions are answered with
**same / replace / omit** — not a rename of UK pages, and not a forced copy
of 55 visible cards.

England’s questionnaire: `src/aequitas/intelligence/section_registry.py` (55
`section_id`s). Ireland’s actions: `src/aequitas/ireland/sections.py`.
NL / FR get the same file shape in Waves 7 / 9 (`netherlands/sections.py`,
`france/sections.py`).

Ranks stay **inside** the country. Never plot IMD vs HP vs SES-WOA vs F-EDI
on one axis. £0 sources only.

**Status (2026-08-13):** England computed. Ireland warehouse CSO-scale
(18,919 SA). Catalogue **36/12/7** (d2–d4 from CSO SAPS). Wave 5 briefing +
Ireland FAISS stamped after PNG pass. Read **§ Ireland mistakes — do not
repeat (NL / FR)** before Wave 7 or 9.

Netherlands warehouse is on disk (Wave 7). France is still catalogue-only.
Do not start France until you have read **§ Ireland mistakes**.

## Ten doors (every country)

Same nav. Same *questions*. Local evidence and statutes.

| Door | England | Ireland | Netherlands | France |
|------|---------|---------|-------------|--------|
| Home | Map + score | Map + score | Map + score | Map + score |
| Equity | IMD / LSOA | HP / Small Area | SES-WOA / buurt | F-EDI or proxy / IRIS |
| Access | BODS 400 m | TFI 400 m | OVapi 400 m | NAP 400 m |
| Service | BODS frequency | TFI `stop_times` | OVapi | NAP |
| Network | HHI 0–10,000 | TFI agencies | OVapi agencies | NAP operators |
| Correlations | IMD matrix | HP matrix + scatter | SES matrix | F-EDI/proxy matrix |
| Economy | TAG / DESNZ | CAF/PAG or PSO + EPA IE | PBL/CBS if free | ADEME/INSEE if free |
| Policy | BSA 2025 | **National policy (NTA)** | OV-wet / concession | AOM / SPC / NAP |
| Scenarios | EN ps1–ps4 | Connecting Ireland / Local Link / BusConnects | OV / flex | SPC / rural holes |
| Reach + Studio | bands + walk-to-stop | same tools, Republic bbox | NL bbox; bus \| all-PT | FR bbox |

Compare stays **inside** the country. Chat (when built) = `FAISS[country]`.

Do **not** require the page to show exactly 55 cards. Correlations stay
**matrix + one scatter + appendix**. Policy/economy/scenarios are **replaced**
programmes, not BSA/TAG with a flag. Omit only when there is no free
small-area variable — NL/FR must **re-check CBS / INSEE** at wave time (do
not copy Ireland’s 10 omits if those countries publish the variable).

## Shared method

| Slot | England | Ireland | Netherlands | France |
|------|---------|---------|-------------|--------|
| GTFS | BODS | TFI `GTFS_All.zip` (Republic) | OVapi | NAP harvest, log holes |
| Small area | LSOA 2021 | CSO Small Area 2022 | Buurt / wijk | IRIS |
| Deprivation | IMD 2025 | Pobal HP 2022 | CBS SES-WOA | F-EDI / FDep / GISD, else Filosofi proxy **never labelled IMD** |
| Urban–rural | Official RUC | CSO or documented density | Stedelijkheid | Official / documented |
| Money / carbon | TAG + DESNZ | CAF/PAG + EPA IE / NTA PSO | Official PBL/CBS if free | Official ADEME/INSEE if free |
| Policy noun | BSA 2025 | Connecting Ireland, BusConnects, Local Link, PSO | Concession / OV-wet (not BSA) | SPC / AOM / NAP (not BSA) |
| Geography word | LSOA, ITL1 | Small Area, county | Buurt, province | IRIS, région |
| Out of pack | — | Northern Ireland | — | DOM unless IRIS+GTFS exist |

Home, ticker, score, Reach bands, Studio walk-to-stop, Compare use the same
method. `0` is a number. `null` is —. Query string must not keep another
country’s region codes (`E12…` on Ireland, etc.).

## Section map

`Action`: **same** = same question, swap inputs; **replace** = new `section_id`
+ title; **omit** = no card, one sentence “no free variable.”

### Access (A)

| id | Question | IE | NL | FR |
|----|----------|----|----|-----|
| a1 | Route density by region | same, by county | same, province | same, région |
| a2 | Stop density | same | same | same |
| a3 | % people within 400 m | same, TFI × SA | same | same |
| a4 | Equity of coverage (Lorenz) | same | same | same |
| a5 | Service deserts | same, people in title | same | same; rural holes honest |
| a6 | Urban vs rural coverage | same | same | same |
| a7 | Investment to reach national average | same, **€** CAF/NTA if free else people-gap only | same, € if free | same, € if free |
| a8 | Coverage ~ demographics (SHAP) | same on HP+SAPS | same SES-WOA | same F-EDI/proxy |

### Service (B)

| id | Question | IE | NL | FR |
|----|----------|----|----|-----|
| b1 | Average frequency | TFI stop_times | OVapi | NAP GTFS |
| b2 | Operating hours | same | same | same |
| b3 | Weekend penalty | same | same | same |
| b4 | Most/least frequent routes | same | same | same |
| b5 | Frequency vs deprivation | vs **HP** | vs SES-WOA | vs F-EDI/proxy |

### Network (C)

| id | Question | IE | NL | FR |
|----|----------|----|----|-----|
| c1 | Route length distribution | same | same | same |
| c2 | Stops per route | same | same | same |
| c3 | Operator HHI | TFI agencies, **0–10,000** | OVapi agencies | NAP operators |
| c4 | Urban vs rural routes | same | same | same |
| c5 | Length vs frequency | same | same | same |
| c6 | Route archetypes | same | same | same |
| c7 | Network topology | same | same | same |

### Correlations (D)

Keep every *metric* in the warehouse. UI: **one matrix + one scatter**
(spec §5.2); appendix can list the rest.

| id | Question | IE | NL | FR |
|----|----------|----|----|-----|
| d1 | Coverage vs deprivation | HP | SES-WOA | F-EDI/proxy |
| d2 | vs unemployment | **same** — CSO SAPS T8 ST+LTU / T8_1_TT (Republic r≈0.010) | CBS if free else omit | Filosofi/INSEE if free |
| d3 | vs no-car | **same** — T15_1_NC / T15_1_TC (r≈0.612) | CBS if free else omit | INSEE if free |
| d4 | vs elderly | **same** — T1 65+ / T1_1AGETT (r≈−0.089) | CBS if free else omit | INSEE if free |
| d5 | vs income | HP/CSO if free | CBS | Filosofi |
| d6 | Transport poverty clusters | same method | same | same |
| d7 | Deprivation × urban/rural | HP × CSO | SES × stedelijkheid | F-EDI × rural |
| d8 | Feature importance | Irish features | NL | FR |
| d9a | vs health domain | HP health cousin or omit | CBS if free | omit if none |
| d9b | vs employment domain | same | same | same |
| d9c | vs crime | omit if no free SA crime | omit/CBS | omit |
| d9d | vs living environment | omit or HP | omit | omit |
| d9e | vs housing/services barriers | omit or HP | omit | omit |

### Equity (F)

| id | Question | IE | NL | FR |
|----|----------|----|----|-----|
| f1 | Gini (Lorenz once) | Gini of Irish service/trips | same | same |
| f2 | Disparity by deprivation decile | **HP decile** slope | SES decile | F-EDI/proxy decile |
| f3 | Access by ethnicity | CSO if free else omit | CBS if free else omit | omit if none |
| f5 | Rural penalty | same | same | same |
| f6 | Most equitable regions | counties | provinces | régions |

### ML (G)

| id | Question | IE | NL | FR |
|----|----------|----|----|-----|
| g1 | Route clusters | same | same | same |
| g2 | Anomalies | same | same | same |
| g3 | Coverage model | same | same | same |
| g4 | SHAP | Irish features | NL | FR |
| g5 | Scenario modelling KPI | points at **Irish** PS list | NL list | FR list |

### Economy (J) — replace UK TAG nouns

| id | England | IE replace | NL replace | FR replace |
|----|---------|------------|------------|------------|
| j1 | Economic value / region | CAF/PAG or NTA PSO value by county | official OV/welzijn if free | AOM/SPC value if free |
| j2 | TAG BCR | **CAF/PAG BCR** or people-only + sentence | Dutch official BCR if free | French official if free |
| j3 | DESNZ carbon | **EPA Ireland** factors | PBL/CBS if free | ADEME if free |
| j4 | Investment priority | counties × HP gap | provinces | régions |

Do not paste TAG 3.5% / 60-year Green Book onto IE/NL/FR unless that is
actually that country’s published rule.

### Policy — replace BSA

| England | Ireland | Netherlands | France |
|---------|---------|-------------|--------|
| bsa1 LTA franchising readiness | Connecting Ireland / NTA programme coverage by county | Concession / OV-wet readiness if free | AOM / SPC organising authority |
| bsa2 operator concentration | may **same** as c3 or drop duplicate | same | same |
| bsa3 readiness tiers | Local Link / BusConnects / Connecting Ireland **tiers** | concession tiers if they exist | AOM tiers if they exist |

Dimension **title** on IE: not “Bus Services Act 2025”. Use “National policy (NTA)” (or NL/FR equivalent).

### Scenarios (PS) — replace EN interventions

| England | Ireland | Netherlands | France |
|---------|---------|-------------|--------|
| ps1 frequency restoration | Restore TFI / Local Link weekday frequency | OV frequency | NAP frequency |
| ps2 evening extension | Evening Local Link / urban TFI | evening OV | evening |
| ps3 rural DRT | Connecting Ireland / rural RTP | rural OV / flex if in GTFS | rural holes honest |
| ps4 combined franchise | Combined Connecting Ireland + BusConnects package (**not** UK franchise) | combined concession | combined SPC |
| ps5 comparison table | compare **those** Irish rows | NL rows | FR rows |

Who × deprivation decile × people. € only with a cited free unit cost.

## Count rule

England has 55 `section_id`s. Each other country must have **55 answers**
(same + replace + omit-with-sentence). Visible cards may be fewer (merged
correlations, unique exhibits).

| Country | same | replace | omit | Code | Warehouse |
|---------|------|---------|------|------|-----------|
| England | 55 computed | — | — | `section_registry.py` | `aequitas.duckdb` live |
| Ireland | 36 | 12 | 7 | `ireland/sections.py` | **18,919 SA** warehouse live; d2–d4 from CSO SAPS |
| Netherlands | **41** | **12** | **2** | `netherlands/sections.py` | **13,827** buurten live; d2–d5/f3/d9a/d9b/d9e from CBS 85984NED; omit d9c crime + d9d environment |
| France | TBD at Wave 9 | policy/economy/scenarios | rural / DOM holes honest | not started | empty |

A seed with Gini/SQI/HHI = 0 and BSA dashes does **not** satisfy this file.
Wave 5 / 7 / 9 is done only when the warehouse is full-scale **and** the
doors show that country’s numbers.

## UI / chrome

- Per-country `DIMENSIONS` titles and headlines.
- Ticker nouns: LSOA | Small Area | buurt | IRIS.
- Insight templates interpolate country, index name, GTFS vintage.
- Unique exhibits: spec §5.2 (one Lorenz, one HHI scale, matrix+scatter).

---

## Ireland briefing — Wave 5 outcome (2026-08-13)

Warehouse **and** briefing **and** `FAISS[ireland]` are stamped with Waves 5
and 6. That stamp is the PNG pass in `qa-visual/wave56-done/` plus the
measured API table in `docs/CURRENT_STATE.md` §11.

What “done” includes: county SVG home; Lorenz; HP decile slope; HHI gauge
0–10,000; HP matrix + one scatter + SHAP; people-gap / illustrative EPA
(no CAF €); National policy (NTA); Irish scenario people tiles; Insight
Engine that names the filter and a number; chat retrieval of Republic
narratives only.

What “done” does **not** include: 15/30/45; a second network date; persisted
c1 `stops_per_route` bins; euro BCR; the seven remaining omits.

Filling a hole with `kpi_tiles` or another 26-county bar is still **not**
the standard for Wave 7 / 9. Read **§ Ireland mistakes** before NL or FR.

---

## Ireland mistakes — do not repeat (NL / FR)

Mandatory reading before Wave 7 (Netherlands) or Wave 9 (France). Same ten
doors and same/replace/omit. **Do not copy Ireland’s implementation path.**

### 1. Declared the country live on a toy seed

Shipped `packReady: true` and home doors on **208 SAs** (8 per county), no
`stop_times`. Scores were ~18.7 everywhere; Gini/SQI/HHI were 0; UI showed
**—**. Cork ≈ Dublin.

**Rule:** `packReady` only after the warehouse is **census-scale** and at
least two regions **differ**. Empty pack = one sentence, not English
furniture with zeros.

### 2. Built chrome before data

Switcher, titles, and 55 `section_id`s existed while Pobal/CSO were missing.
The page looked like a product and computed nothing.

**Rule:** ingest → writers → then doors. A census of empty `chart_data` is a
fail, not a “questionnaire done.”

### 3. Photocopied England instead of answering the question

- BSA / TAG / LSOA / IMD / £ on Irish pages (or “not applicable” graves).
- Caveats that **named** BODS/IMD/TAG/BSA so QA flagged UK nouns.
- Ticker said LSOAs; Studio h1 “England”; Reach “Unmatched LSOAs / ITL1.”
- Economy used a pound icon. Query kept `E12…`, `a=`, `franchise`.
- `n_lsoas` in Ireland stats. `formatHeadline(0) → "—"`.

**Rule:** local nouns from day one (buurt / IRIS, SES-WOA / F-EDI, €,
province / région). Deny UK statutes **without** repeating their names in
the body. Strip the other country’s query keys on switch. `0` is `0.0`.

### 4. Factory charts, then kpi_tiles as a patch

Most IDs had **no `chart_data.type`**. Many “fixes” were another
**26-county bar** or **`kpi_tiles` pointing at another door**. HHI was
“routes per agency.” `f2` was a bar, not a decile slope. Correlations were
not matrix + one scatter.

**Rule:** spec §5.2 **before** the first chart. One Lorenz, one HHI
0–10,000, paired urban–rural dots, desert choropleth with **people** in the
title, matrix + scatter. Two different questions must not share an encoding.
`kpi_tiles` is not an exhibit.

### 5. Insight Engine was a one-liner

Narratives did not name the filter. One template-ish sentence for the
Republic was reused in spirit. Palma 0.000 looked like a broken England 5.7
until someone explained **zero weekday trips in the bottom 40%**.

**Rule:** Key finding → so what → caveat; interpolate country, region,
urban/rural, n areas, GTFS vintage, **local** index. Weird zeros get a
sentence, not a silent 0.000.

### 6. Official files fail in ways we then faked around

`pobal.ie` timed out. First CSO “SAPS” hit was the **wrong table** (historical
county census). HP on data.gov.ie is **ED-level** (3,417), joined via
`ED_ID_STR` (99.11%) — that is honest, not SA-level HP.

**Rule:** verify row counts vs the statistical office. Document the URL that
worked. Never invent deciles. NL/FR: do not copy Ireland’s **10 omits** if
CBS/INSEE publish the variable. Re-check at wave time.

### 7. Map and bbox were England-shaped

Home map was **boxes** on a GB frame. Studio used England region names.
Clicks in Birmingham had to be special-cased late.

**Rule:** country polygons first; fit **that** country; Studio bbox =
Republic / NL / FR only. Northern Ireland stays out of Ireland.

### 8. Chat and 15/30/45 were implied “live”

For most of Wave 5 there was no `FAISS[ireland]` and the drawer still
offered BSA / IMD. 15/30/45 never ran. Compare 45-min stayed empty.

**Now (Ireland only, 2026-08-13):** `data/ireland/faiss_index.bin` (4,457
chunks from Ireland narratives). Drawer is country-keyed. 15/30/45 is still
an honest empty sentence.

**Rule:** chat only after real narratives + a **country** index. 15/30/45
only after `aequitas reach` for that country. Until then the UI says so.
NL/FR must not copy England or Ireland chunks into the other drawer.

### 9. Marked the wave done too early

CURRENT_STATE said Ireland was live / Wave 5 done while the seed, then
while hollow cards, then while `kpi_tiles` stood in for exhibits.
Agents treated an API census or Playwright **body-text** sweep as a visual
pass. Lorenz was “done” because a Gini number existed.

**Rule:** three checkboxes — **warehouse** · **briefing quality** · **chat**.
Warehouse ≠ briefing. Briefing ≠ chat. A pass is a **screenshot of the
exhibit**, not `#root` non-empty.

### 10. England-shaped map after MapLibre aborted

Home and desert/policy choropleths showed a **GB CARTO frame** + “Map
boundaries could not be loaded.” `maplibre-gl.js` **ERR_ABORTED**. Geography
defaulted to ITL1. Ireland had no `ireland_county` encoding / SVG fallback.

**Rule:** set `geography` for that country on every choropleth. If the GL
chunk dies, draw **local polygons** (26 counties / CBS gemeenten / FR
départements) — never leave an England tile stack under another flag.
Studio bbox = that country only. NI / DOM out unless in the pack.

### 11. Export, ticker, time, and chat leaked England

- `GET /api/export/pack.csv?country=ireland` said **England / BODS**.
- `GET /api/time?pack=2099-01-01` returned **200 + the current point**.
- Unknown pack on an Ireland URL: ticker **“Pack not built / England is live.”**
- Chat suggestions were **BSA / IMD**. Quick Actions stayed “Explore Inequality.”
- `/time` copy said **BODS** on Ireland. Footer said **DfT**.
- Studio “Listed scenarios” linked **`/app/england/scenarios`**.
- Country switch kept `E12…`, `dublin`, or the other country’s `pack`.

**Rule:** every string (CSV, HTML pack, ticker, time 404, chat chips, footer,
Studio links) is **country-keyed**. Unknown pack = **404**, never silent
current. Switcher **drops** the other country’s keys. Chat without
`FAISS[country]` says the index is not built — no other country’s statutes.

### 12. Wrong warehouse slug = empty door

`/app/ireland/economic` (warehouse id) rendered **“— Ireland”** while
`/economy` is the product door. ScenarioBuilder (TAG sliders) mounted on
Ireland.

**Rule:** product slugs only; warehouse ids redirect. England-only widgets
(`ScenarioBuilder`, TAG sliders) must not mount on other countries.

### 13. Correlations and economy were a factory

Correlations shipped **18 cards** (omit graves + g* clones). Economy was
`kpi_tiles` / a fake BCR **—**. Fix that lasted: **one HP matrix + one
scatter + SHAP + one omit sentence**; economy = people-gap + illustrative
EPA **without invented CAF €**.

**Rule:** spec §5.2. Do not invent a euro BCR. NL/FR: PBL/CBS or ADEME
**only if a free unit cost exists**.

### 14. Official files we almost faked (repeat for agents)

`pobal.ie` HTTP 28. First CSO hit was a **historical county** table. HP on
data.gov.ie is **ED-level** (3,417) joined SA→ED (`ED_ID_STR` 99.11%).
Palma **0.000** is real (bottom 40% SAs have no weekday TFI trips), not a
broken England 5.7.

**Rule:** row counts vs the NSI. Document the URL that worked. Never invent
deciles. Do **not** copy Ireland’s 10 omits if CBS/INSEE publish the variable.

### NL traps we actually hit (2026-08-14 visual pass)

Do not treat these as Done just because the warehouse is census-scale.

1. **SES join 70.5%** — 86092NED BU keys 14,574; only ~70.5% of populated buurten get a SES-WOA score. Remaining SES is null. Do not invent deciles for the rest.
2. **`mode=bus` vs `mode=all`** — bus 53,157 stops / HHI ~1333; all-PT 55,801 / HHI ~1162. National score 70.6 vs 72.0. Rounding both to 71 hides the mode. Overview, ticker, and score must pass `mode`.
3. **Ticker treated NL as empty** — frontend only fetched EN/IE. Live NL then showed “unknown network date” on the current pack.
4. **`/time` copied Ireland then England copy** — CSO / Pobal / BODS / IMD / LSOA on a Netherlands page. Frozen line is CBS buurten / SES-WOA / OVapi only.
5. **Reach loaded England bands** — `load_bands_frame` fell through to the England parquet. NL must return an honest empty, never 33,755 LSOAs or an Ireland/GB frame.
6. **Compare defaulted to E12…** — Drenthe selected in the dropdown, slopes labelled E12000002 / E12000007. Defaults are Groningen / Noord-Holland.
7. **Chat offered BSA / England** — no `FAISS[netherlands]`. Drawer must say “Netherlands index not built” and not retrieve EN/IE chunks.
8. **Unknown pack spun “Loading…”** — 404 retried; `isLoading` hid the error. 404 is a sentence, not a pulse.
9. **Policy title “LTA franchising readiness”** — tab said Concession / OV-wet; card title still UK. `sectionTitle` must be country-keyed.
10. **Sunday deserts 100% / correlations all 0.0** — Sunday was a **calendar join** bug (OVapi ships `calendar_dates.txt` only). After the join: 49.6% bus, not 100%. Heatmap zeros were the UI reading `values` while writers emitted `z`. Closed in writers; do not re-introduce `calendar.txt`-only Sunday flags.
11. **Imputed SES=0 changes the national score.** Filling unmatched SES-WOA with 0 produced 70.6 / 72.0. Dropping nulls for r produced 69.6 / 71.1. Do not invent decile 5. State n with SES vs n without.
12. **GaugeChart ignores `value`.** HHI must send `markers` + band `color_hint` or the first Network card is “No data available” while tiles show 1,333.
13. **Dual-mode warehouse insert can SIGTRAP** after two 2,145-row precomputes. Write bus, then append `mode=all`. Never overwrite EN/IE duckdbs while doing this.
14. **Fryslân / friesland + leftover `Unknown` bars.** **Closed (2026-08-14 cleanup).** Home map matches GeoJSON `name` (`friesland`), not the display string Fryslân (dropdown stays Fryslân). Leftover buurten are excluded from provincie bars with an honest n — not a 14th provincie.

### NL / FR checklist (gate)

Before calling Wave 7 or 9 done:

- [ ] Census-scale warehouse; two regions’ scores **differ** (not 208-row seed)
- [ ] `packReady` only after that; empty pack = one sentence
- [ ] Ingest → writers → doors (no chrome-on-empty)
- [ ] Local index, geography words, money, policy **titles** (not BSA/TAG/IMD)
- [ ] Catalogue same/replace/omit **re-derived** from CBS/INSEE, not copied
- [ ] Every non-omit section has a **distinct** exhibit (§5.2); `kpi_tiles` ≠ exhibit
- [ ] Narratives name the **filter** and a real number; no UK noun leakage
- [ ] Province/région (or county) **polygons**; SVG fallback if MapLibre aborts
- [ ] Studio bbox = that country; no England region names or `/app/england/…` links
- [ ] Export CSV/HTML nouns = that country’s GTFS + census + deprivation
- [ ] Unknown `pack=` **404**s time **and** ticker (no “England is live”)
- [ ] Chat: `FAISS[country]` or honest “index not built”; suggestions local
- [ ] Product slugs only (`/economy` not `/economic`); England widgets gated
- [ ] 15/30/45 honest or real after `aequitas reach` for **that** country
- [ ] England **and** Ireland regression still green
- [ ] Briefing quality called out separately from “pack on disk”
- [ ] Visual pass = screenshots of exhibits, not a text scrape of 80 loads
