# Aequitas — Academic Paper Strategy
*For independent researcher — compiled 2026-05-25*

---

## RECOMMENDED JOURNAL: Transport Policy (Elsevier)

**Why:** Publishability score 9/10. Perfect topical fit — explicitly publishes bus/transit equity, UK deprivation analysis, and Bus Services Act coverage. JIF 6.8 (Q1). Accepts independent/unaffiliated researchers. Free to publish (subscription route). APC waiver possible if needed.

**Submission address:** Submit via Elsevier Editorial System (EES). Affiliation field: "Independent Researcher, United Kingdom"

---

## JOURNAL RANKING TABLE

| Rank | Journal | JIF 2023 | Quartile | APC (Gold OA) | Accept rate | Score |
|---|---|---|---|---|---|---|
| 1 | **Transport Policy** (Elsevier) | 6.8 | Q1 | £2,790 | ~25–30% | **9/10** |
| 2 | Journal of Transport Geography (Elsevier) | 4.7 | Q1 | £2,460 | ~20–25% | **8.5/10** |
| 3 | Applied Geography (Elsevier) | 4.0 | Q1 | £2,450 | ~30% | **8/10** |
| 4 | Transportation Research Part A (Elsevier) | 5.3 | Q1 | £2,790 | ~18–22% | **7.5/10** |
| 5 | Journal of Transport & Health (Elsevier) | 3.6 | Q2 | £1,990 | ~35–40% | **7/10** |
| 6 | Env & Planning B: Urban Analytics (SAGE) | 4.2 | Q1 | £2,600 | ~25–30% | **6.5/10** |
| 7 | Urban Studies (SAGE) | 4.5 | Q1 | £2,800 | ~12–18% | **6/10** |
| 8 | PLOS ONE | 2.9 | Q2 | $1,930 USD | ~50–60% | **6/10** |
| 9 | Social Science & Medicine (Elsevier) | 5.4 | Q1 | £2,500 | ~15–20% | **5.5/10** |
| 10 | JRSS Series A (Wiley) | 3.9 | Q1 | £3,360 | ~15% | **4.5/10** |

---

## PAPER REQUIREMENTS (Transport Policy)

| Requirement | Specification |
|---|---|
| Word limit | 8,000–10,000 words (body); max ~12,000 incl. references |
| Abstract | Unstructured, **250 words max** |
| Sections | Introduction → Literature → Data & Methods → Results → Discussion → Policy Implications → Conclusions |
| Highlights | **3–5 bullet highlights** required at submission (1 line each, key findings) |
| Reference style | **APA 7th** (author-year in text) |
| Figures | No hard cap; **8–12 figures typical** for spatial/equity papers |
| Tables | No cap; **4–6 tables typical** |
| Supplementary | Yes — appendices, code links, extended data tables |
| Time to decision | 6–10 weeks (median ~8 weeks) |
| OA route | Subscription (free) — no APC needed |
| OA waiver | Request via Elsevier discretionary process if Gold OA wanted |

---

## PAPER STRUCTURE

### Title (recommended)
**"Bus Service Inequality in England: A Multi-Dimensional Analysis across 33,755 Lower Super Output Areas"**

Alternative: *"Beyond Coverage: Measuring and Explaining Bus Transport Inequity in England Using Open Government Data and Machine Learning"*

### Abstract (250 words — draft)
England's bus network exhibits profound service inequality that is poorly captured by aggregate statistics. This paper presents the first comprehensive multi-dimensional analysis of bus transport equity across all 33,755 Lower Super Output Areas (LSOAs) in England, integrating eight open government datasets spanning 274,719 bus stops, 13,099 routes, and 56,490,056 residents. We compute Gini (0.574), Palma ratio (5.70), and Concentration Index (+0.136) for service distribution, revealing inequality that exceeds the UK income Gini (0.36) and exhibits pro-rich bias. Using the two-step floating catchment area (2SFCA) method, we find 79.9% of England's population lives within 400m of a bus stop nationally, masking a 50-percentage-point urban–rural divide (urban 88.2%; rural 38.0%). A four-times disparity in trips per capita separates London (0.53) from East of England (0.125). Random Forest modelling (R²=0.472) with SHAP decomposition identifies car ownership as the primary predictor of service coverage — not deprivation — indicating a structural self-reinforcing inequity: areas with low car ownership receive more service, but these are predominantly urban areas, leaving rural car-dependent populations doubly disadvantaged. Economic appraisal using HM Treasury Green Book methodology quantifies a £1.19 billion investment gap and a benefit-cost ratio of 1.17. Under the Bus Services Act 2025, only 38 of 298 local authority districts achieve franchising readiness Tier 1 (Good), with London accounting for 26 of these. We provide a reproducible pipeline and open dataset for policy makers at national and local level.

### Sections and word budget

| Section | Words | Content |
|---|---|---|
| 1. Introduction | 600 | Transport justice gap, BSA 2025 context, paper contribution |
| 2. Literature Review | 1,000 | Transport deprivation lit, inequality measurement (Gini for services), 2SFCA history, UK bus decline post-2010 |
| 3. Data & Methods | 1,500 | 8 datasets (Table 1), 2SFCA method, Gini/Palma/CI formula, RF + SHAP, BCR/TAG framework |
| 4. Results | 3,000 | 4.1 Equity nationally/regionally, 4.2 Accessibility & deserts, 4.3 Correlates & ML, 4.4 Economic appraisal, 4.5 BSA readiness |
| 5. Discussion | 1,500 | Pro-rich bias interpretation, car dependency trap, London effect, policy implications |
| 6. Conclusions | 400 | Key recommendations, limitations, open data |
| References | ~800 | APA 7th, ~50–70 references |
| **Total** | **~8,800** | Within Transport Policy range |

---

## FIGURES FOR PAPER (select 8–10)

All data is live in the app. These are directly exportable from the 49 available charts.

| # | Section | Chart type | Content | Data source |
|---|---|---|---|---|
| F1 | Equity | **Lorenz curve** | Bus service distribution vs. line of equality | f1_gini / a4_coverage_equity |
| F2 | Equity | **Horizontal bar** | Gini by region (9 regions) | f6_equitable_regions |
| F3 | Accessibility | **Grouped bar** | 400m coverage % by region × urban/rural | a3_walking_distance |
| F4 | Accessibility | **Horizontal bar** | Service desert LSOAs by region (evening + Sunday) | a5_service_deserts |
| F5 | Correlations | **Scatter regression** | Coverage vs. IMD deprivation score (n=33,755) | d1_coverage_deprivation |
| F6 | Correlations | **Scatter regression** | Coverage vs. car ownership % (r=0.403) | d3_coverage_car |
| F7 | ML / SHAP | **SHAP bar chart** | Feature importance for RF coverage model | g4_shap |
| F8 | Route Network | **Scatter clusters** | Route archetypes (8 clusters) | g1_route_clusters |
| F9 | BSA 2025 | **Stacked bar** | Franchising readiness tiers by region | bsa3_tier_distribution |
| F10 | Economic | **Horizontal bar** | Investment gap by region (£M) | j4_investment_priority |

Optional (if space permits):
- Heatmap: deprivation decile × urban/rural service level (d7_deprivation_urban_rural)
- Choropleth: geographic coverage map (c7_network_topology)

---

## TABLES FOR PAPER (5 core)

All data extracted from live API (2026-05-25).

### Table 1 — Data Sources
| Dataset | Source | Records | Date |
|---|---|---|---|
| NaPTAN bus stops | DfT Open Data | 274,719 active | 2024 |
| BODS GTFS routes | Bus Open Data Service | 13,099 unique routes | 2024 |
| BODS trips | BODS GTFS | 1,752,443 trips | 2024 |
| Census 2021 LSOAs | ONS | 33,755 LSOAs | 2021 |
| England population | ONS TS001 | 56,490,056 | 2021 |
| IMD 2025 | MHCLG | 33,755 LSOAs | 2025 |
| NHS facilities | NHS ODS | 3,714 hospitals; 12,059 GPs | 2024 |
| Employment (BRES) | NOMIS | 6,791 MSOAs, 27.3M employees | 2023 |

### Table 2 — Regional Summary
| Region | Gini | Palma | 400m_cov% | Trips/cap | BCR | Inv_Gap_£M | BSA_rdns% |
|---|---|---|---|---|---|---|---|
| All England | 0.574 | 5.70 | 79.9 | 0.252 | 1.17 | 1,193.7 | 62.6 |
| North East | 0.432 | 2.21 | 85.6 | 0.276 | 1.16 | 27.7 | 70.6 |
| North West | 0.512 | 3.74 | 83.4 | 0.223 | 1.14 | 143.9 | 67.7 |
| Yorkshire & Humber | 0.520 | 4.18 | 79.2 | 0.285 | 1.17 | 86.4 | 65.9 |
| East Midlands | 0.526 | 3.93 | 73.0 | 0.196 | 1.18 | 107.9 | 57.7 |
| West Midlands | 0.549 | 4.97 | 82.3 | 0.219 | 1.17 | 129.2 | 56.7 |
| East of England | 0.538 | 4.71 | 70.8 | 0.125 | 1.18 | 199.0 | 54.3 |
| London | 0.526 | 4.44 | 95.7 | 0.532 | 1.12 | 107.8 | 82.8 |
| South East | 0.572 | 5.97 | 75.1 | 0.168 | 1.16 | 259.2 | 59.6 |
| South West | 0.528 | 4.02 | 73.8 | 0.194 | 1.20 | 125.3 | 59.4 |

### Table 3 — Urban vs Rural Coverage
| Region | All% | Urban% | Rural% | Gap (pp) |
|---|---|---|---|---|
| All England | 79.9 | 88.2 | 38.0 | 50.2 |
| North East | 85.6 | 91.6 | 56.6 | 35.0 |
| North West | 83.4 | 88.4 | 35.2 | 53.2 |
| Yorkshire | 79.2 | 87.3 | 37.7 | 49.6 |
| East Midlands | 73.0 | 85.1 | 37.8 | 47.3 |
| West Midlands | 82.3 | 90.9 | 31.4 | 59.5 |
| East of England | 70.8 | 83.1 | 37.7 | 45.4 |
| London | 95.7 | 95.7 | N/A | — |
| South East | 75.1 | 83.6 | 37.6 | 46.0 |
| South West | 73.8 | 88.1 | 39.0 | 49.1 |

### Table 4 — Socio-Economic Correlations (Pearson r, n=33,755 LSOAs)
| Factor | National r | Interpretation |
|---|---|---|
| Car ownership (nocar_pct) | +0.403 | Strongest predictor; also top SHAP feature |
| Unemployment rate | +0.207 | Moderate positive |
| IMD deprivation score | +0.141 | Weak positive (urban concentration effect) |
| Income deprivation | +0.126 | Weak positive |
| Elderly population (65+) | **−0.193** | Negative — elderly in rural areas worst served |

### Table 5 — BSA 2025 Readiness Tier Distribution
| Region | Tier 1 (Good) | Tier 2 (Above avg) | Tier 3 (Below avg) | Tier 4 (Poor) | n_LADs |
|---|---|---|---|---|---|
| All England | 38 (12.8%) | 133 (44.6%) | 107 (35.9%) | 20 (6.7%) | 298 |
| London | 26 (76.5%) | 8 (23.5%) | 0 | 0 | 34 |
| North East | 5 (38.5%) | 7 (53.8%) | 0 | 1 (7.7%) | 13 |
| North West | 1 (2.9%) | 28 (80.0%) | 6 (17.1%) | 0 | 35 |
| Yorkshire | 0 | 12 (80.0%) | 3 (20.0%) | 0 | 15 |
| East Midlands | 1 (2.9%) | 14 (40.0%) | 16 (45.7%) | 4 (11.4%) | 35 |
| West Midlands | 0 | 10 (33.3%) | 16 (53.3%) | 4 (13.3%) | 30 |
| East of England | 1 (2.2%) | 16 (34.8%) | 21 (45.6%) | 8 (17.4%) | 46 |
| South East | 4 (6.3%) | 26 (40.6%) | 32 (50.0%) | 2 (3.1%) | 64 |
| South West | 0 | 12 (46.2%) | 13 (50.0%) | 1 (3.8%) | 26 |

---

## KEY CLAIMS FOR THE PAPER (evidence-graded)

| Claim | Value | Source | Strength |
|---|---|---|---|
| Bus Gini exceeds UK income Gini | 0.574 vs 0.36 | ONS + 04c notebook | Strong |
| Pro-rich concentration bias | CI = +0.136 | 04c notebook | Strong |
| 5.7× Palma ratio | 5.702 | 04c notebook | Strong |
| 50pp urban–rural coverage gap | 88.2% vs 38.0% | a3_walking_distance | Strong |
| 4.1× London–East of England trip gap | 0.53 vs 0.125 | b1_frequency | Strong |
| Car ownership top ML predictor | SHAP rank 1 | g4_shap, R²=0.472 | Moderate (R² explains 47%) |
| £1.19B investment gap | 1,193.7M | j4 (BCR framework) | Moderate (parametric) |
| BCR 1.17 | 1.17 | j2_bcr | Moderate |
| Only 12.8% LADs franchise-ready | 38/298 | bsa3 | Strong |
| 612 triple-deprived LSOAs | 1.8% | 04c | Strong |
| 15.4% evening-isolated LSOAs | 5,189 | 04b | Strong |
| 20% Sunday desert LSOAs | 6,745 | 04b | Strong |

---

## LIMITATIONS TO ADDRESS IN THE PAPER

1. **Cross-sectional snapshot** — BODS/NaPTAN data from 2024; no longitudinal trend (post-Covid recovery not separated from structural inequity)
2. **BCR parametric model** — investment gap uses national average cost assumptions; regional cost variations not modelled
3. **ML R² = 0.472** — 47% explained variance; 53% from unobserved factors (local history, geography, political economy)
4. **2SFCA catchment** — 400m Euclidean buffer; ignores road network, hills, accessibility for mobility-impaired
5. **GTFS data completeness** — 48.5% of trips lack shape_id; route geometries estimated via Haversine for 7,241/13,099 routes
6. **IMD 2025 vs Census 2021** — 4-year gap between deprivation and population data
7. **HHI national only** — operator concentration index is England-wide; no local market disaggregation

---

## OVERLEAF WORKFLOW

### Structure
```
main.tex
├── sections/
│   ├── 01_introduction.tex
│   ├── 02_literature.tex
│   ├── 03_methods.tex
│   ├── 04_results.tex
│   ├── 05_discussion.tex
│   └── 06_conclusions.tex
├── figures/          (export from app as PNG/SVG)
├── tables/           (copy from this document)
└── references.bib    (APA 7th via Zotero/BibTeX)
```

### Transport Policy Elsevier template
Use the **Elsevier article class**: `\documentclass[review]{elsarticle}` with `cas-sc` or standard `elsarticle` template. Available on Overleaf directly.

### Figure export from Aequitas app
- Run app locally: backend port 8000, frontend port 5173
- Each chart renders as SVG/Canvas in browser
- Screenshot or use browser DevTools → right-click → "Save as SVG" for vector charts
- For Overleaf: export as PDF-compatible SVG or high-DPI PNG (300 DPI minimum)

---

## SUBMISSION CHECKLIST (Transport Policy)

- [ ] Title page (title, author name, "Independent Researcher, UK", email, ORCID if available)
- [ ] Abstract (max 250 words, unstructured)
- [ ] Highlights (3–5 bullet points, max 85 chars each)
- [ ] Keywords (5–8; e.g.: bus transport equity, Gini coefficient, spatial inequality, England, LSOA, accessibility, Bus Services Act 2025)
- [ ] Main manuscript (8,000–10,000 words)
- [ ] Figures (8–10, numbered F1–F10, captions in manuscript)
- [ ] Tables (5, numbered T1–T5, captions in manuscript)
- [ ] Supplementary material (full data tables, Python code, methodology appendix)
- [ ] Data availability statement (link to GitHub/Zenodo repo)
- [ ] Declaration of competing interests (none)
- [ ] Funding statement (independent/unfunded — state this)
- [ ] Ethics statement (not required — no human subjects)

---

## FALLBACK SUBMISSION SEQUENCE

1. **Transport Policy** (primary, ~8 weeks to decision)
2. **Journal of Transport Geography** (if rejected; spatial methods emphasis)
3. **Applied Geography** (if rejected; tighter methods focus)
4. **PLOS ONE** (backstop; open access; highest acceptance rate; free if waiver granted)
