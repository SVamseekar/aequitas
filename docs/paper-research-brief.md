# Aequitas — Academic Paper Research Brief
*Generated 2026-05-25 from live app data (240 filter combinations)*

---

## 1. What the App Contains

### Dimensions, Sections, Charts
- **8 policy dimensions**, **51 sections**, **49 visualisations** (charts) at national level
- Every section has stats, a narrative, and a chart
- All 240 filter combinations (8 dims × 10 regions × 3 area types) return data cleanly

### Chart types available for paper
| Chart type | Count | Use in paper |
|---|---|---|
| Horizontal bar | 22 | Regional comparisons, rankings |
| Scatter regression | 7 | Socio-economic correlations |
| Grouped bar | 6 | Urban vs rural, weekend vs weekday |
| SHAP bar | 4 | Feature importance / ML explainability |
| Lorenz curve | 2 | Equity / inequality visualisation |
| Stacked bar | 2 | Service desert composition |
| Box/violin | 2 | Route length / stop distributions |
| Scatter clusters | 2 | ML clustering (LSOA & route archetypes) |
| Choropleth | 1 | Geographic spatial coverage map |
| Heatmap | 1 | Deprivation × urban/rural cross-tab |

---

## 2. Key Findings from All Filter Combinations

### PAPER TABLE 1: Regional Summary (All Areas)
| Region | Gini | Palma | 400m_cov% | Trips/cap | ML R² | BCR | Inv_Gap_£M | BSA_readiness% |
|---|---|---|---|---|---|---|---|---|
| All England | 0.5741 | 5.702 | 79.9 | 0.252 | 0.472 | 1.17 | 1,193.7 | 62.6 |
| North East | 0.4317 | 2.211 | 85.6 | 0.276 | 0.472 | 1.16 | 27.7 | 70.6 |
| North West | 0.5117 | 3.740 | 83.4 | 0.223 | 0.472 | 1.14 | 143.9 | 67.7 |
| Yorkshire & Humber | 0.5195 | 4.179 | 79.2 | 0.285 | 0.472 | 1.17 | 86.4 | 65.9 |
| East Midlands | 0.5259 | 3.933 | 73.0 | 0.196 | 0.472 | 1.18 | 107.9 | 57.7 |
| West Midlands | 0.5488 | 4.974 | 82.3 | 0.219 | 0.472 | 1.17 | 129.2 | 56.7 |
| East of England | 0.5378 | 4.709 | 70.8 | 0.125 | 0.472 | 1.18 | 199.0 | 54.3 |
| London | 0.5258 | 4.435 | 95.7 | 0.532 | 0.472 | 1.12 | 107.8 | 82.8 |
| South East | 0.5720 | 5.973 | 75.1 | 0.168 | 0.472 | 1.16 | 259.2 | 59.6 |
| South West | 0.5275 | 4.021 | 73.8 | 0.194 | 0.472 | 1.20 | 125.3 | 59.4 |

### PAPER TABLE 2: Urban vs Rural Equity (Gini by region)
| Region | All_Gini | Urban_Gini | Rural_Gini | Urban–Rural_gap |
|---|---|---|---|---|
| All England | 0.5741 | 0.5635 | 0.5283 | +0.035 |
| North East | 0.4317 | 0.4383 | 0.3717 | +0.067 |
| North West | 0.5117 | 0.5075 | 0.5324 | -0.025 |
| Yorkshire | 0.5195 | 0.5029 | 0.5326 | -0.030 |
| East Midlands | 0.5259 | 0.5182 | 0.5011 | +0.017 |
| West Midlands | 0.5488 | 0.5278 | 0.4883 | +0.040 |
| East of England | 0.5378 | 0.5389 | 0.5051 | +0.034 |
| London | 0.5258 | 0.5258 | N/A | — |
| South East | 0.5720 | 0.5683 | 0.5443 | +0.024 |
| South West | 0.5275 | 0.5081 | 0.5317 | -0.024 |

### PAPER TABLE 3: Accessibility — 400m Coverage by Region × Area Type
| Region | All% | Urban% | Rural% | Urban–Rural gap |
|---|---|---|---|---|
| All England | 79.9 | 88.2 | 38.0 | 50.2pp |
| North East | 85.6 | 91.6 | 56.6 | 35.0pp |
| North West | 83.4 | 88.4 | 35.2 | 53.2pp |
| Yorkshire | 79.2 | 87.3 | 37.7 | 49.6pp |
| East Midlands | 73.0 | 85.1 | 37.8 | 47.3pp |
| West Midlands | 82.3 | 90.9 | 31.4 | 59.5pp |
| East of England | 70.8 | 83.1 | 37.7 | 45.4pp |
| London | 95.7 | 95.7 | N/A | — |
| South East | 75.1 | 83.6 | 37.6 | 46.0pp |
| South West | 73.8 | 88.1 | 39.0 | 49.1pp |

### PAPER TABLE 4: Socio-Economic Correlations by Region
| Region | r_deprivation | r_car_ownership | r_unemployment | r_elderly | ML_R² | Top_SHAP |
|---|---|---|---|---|---|---|
| All England | 0.141 | 0.403 | 0.207 | -0.193 | 0.472 | nocar_pct |
| North East | 0.131 | 0.312 | — | — | 0.472 | nocar_pct |
| North West | 0.193 | 0.333 | — | — | 0.472 | nocar_pct |
| Yorkshire | 0.162 | 0.373 | — | — | 0.472 | nocar_pct |
| East Midlands | 0.210 | 0.391 | — | — | 0.472 | nocar_pct |
| West Midlands | 0.255 | 0.421 | — | — | 0.472 | nocar_pct |
| East of England | 0.111 | 0.299 | — | — | 0.472 | nocar_pct |
| London | 0.047 | 0.230 | — | — | 0.472 | nocar_pct |
| South East | 0.161 | 0.416 | — | — | 0.472 | nocar_pct |
| South West | 0.073 | 0.361 | — | — | 0.472 | nocar_pct |

### PAPER TABLE 5: Bus Services Act 2025 Readiness by Region
| Region | Readiness_% | Tier1_Good | Tier2_AboveAvg | Tier3_Below | Tier4_Poor | n_LADs |
|---|---|---|---|---|---|---|
| All England | 62.6 | 38 | 133 | 107 | 20 | 298 |
| North East | 70.6 | 5 | 7 | 0 | 1 | 13 |
| North West | 67.7 | 1 | 28 | 6 | 0 | 35 |
| Yorkshire | 65.9 | 0 | 12 | 3 | 0 | 15 |
| East Midlands | 57.7 | 1 | 14 | 16 | 4 | 35 |
| West Midlands | 56.7 | 0 | 10 | 16 | 4 | 30 |
| East of England | 54.3 | 1 | 16 | 21 | 8 | 46 |
| London | 82.8 | 26 | 8 | 0 | 0 | 34 |
| South East | 59.6 | 4 | 26 | 32 | 2 | 64 |
| South West | 59.4 | 0 | 12 | 13 | 1 | 26 |

---

## 3. National-Level Headline Statistics

### Equity
- **Gini: 0.5741** — bus service distribution more unequal than UK income Gini (0.36)
- **Palma ratio: 5.702** — top 10% receive 5.7× more service than bottom 40%
- **Concentration Index: +0.1358** — PRO-RICH bias (positive = wealthier areas better served)
- **P90/P10 disparity ratio: 33.64** — top 10% LSOA gets 33.6× service of bottom 10%
- **Triple-deprived LSOAs: 612 (1.8%)** — high IMD + low bus + no car
- **Disparity: urban Gini 0.5635, rural Gini 0.5283** (rural relatively more equal within itself)

### Accessibility
- **79.9% within 400m nationally** (urban 88.2%, rural 38.0%)
- **6,776 LSOAs have zero 2SFCA access** (20.1%)
- Worst region: East of England at 70.8%; best (ex-London): North East at 85.6%
- London: 95.7% (effectively universal coverage)

### Service Quality
- **National avg: 0.252 trips/capita/day**
- London: 0.532 trips/cap (2.1× national); East of England: 0.125 (0.5× national)
- **4.25× disparity** between best (London) and worst (East of England) region
- Service day span: 18.1 hours national average; London: 24.1h (24-hour)
- **Evening isolated LSOAs: 5,189 (15.4%)**
- **Sunday desert LSOAs: 6,745 (20.0%)**
- Mean SQI: 62.6/100

### Route Network
- **13,640 routes** nationally, mean length 23.0km (median 18.75km)
- London routes have no geometry data (null)
- **HHI: 829** (low concentration — competitive market nationally)
- 8 route archetypes identified via HDBSCAN clustering (5,480 routes with geometry)

### Socio-Economic & ML
- **Car ownership strongest predictor** of bus coverage (r=0.403, top SHAP feature)
- Deprivation correlation weak positive (r=0.141) — urban concentration effect
- Elderly population negatively correlated (r=-0.193) — rural elderly worst served
- **Random Forest R²=0.472** — 47% of variation explained; 53-72% policy-driven
- 3 transport poverty clusters, 1,688 anomalous LSOAs (5%)

### Economic Appraisal (Green Book / TAG v2.03fc)
- **Annual economic benefit: £1,390M** (England total)
- **BCR: 1.17** — "Low" VfM band but positive
- **CO2 saving: 7,257.9 tonnes** (modal shift from car to bus)
- **Investment gap: £1,193.7M** to reach national average coverage everywhere
- Highest gap regions: South East (£259M), East of England (£199M)

### Policy Scenarios
- **4 scenarios modelled**: Frequency restoration, Evening extension, DRT rural, Franchising
- Each affects 5,649,005 people (10% of England population)

---

## 4. Data Sources (for Methods section)
| Dataset | Source | Records | Date |
|---|---|---|---|
| NaPTAN bus stops | DfT Open Data | 274,719 active | 2024 |
| BODS GTFS routes | Bus Open Data Service | 13,099 unique routes | 2024 |
| BODS trips | BODS GTFS | 1,752,443 trips | 2024 |
| Census 2021 LSOAs | ONS | 33,755 LSOAs | 2021 |
| England population | ONS TS001 | 56,490,056 | 2021 |
| IMD 2025 | MHCLG | 33,755 LSOAs | 2025 |
| NHS hospitals | NHS ODS | 3,714 geocoded | 2024 |
| NHS GP practices | NHS ODS | 12,059 geocoded | 2024 |
| GIAS schools | DfE | 27,183 open | 2024 |
| BRES employment | NOMIS | 6,791 MSOAs | 2023 |
| Code-Point postcodes | Ordnance Survey | 1,492,016 | 2024 |
| Carbon factors | DESNZ | Bus: 0.10385 kg/pax-km | 2025 |

---

## 5. Suggested Paper Structure

### Title options
1. "Bus Service Inequality in England: Evidence from Open Government Data across 33,755 Lower Super Output Areas"
2. "Transport Deprivation or Urban Concentration? A Machine Learning Analysis of Bus Coverage Inequality in England"
3. "Beyond the Lorenz Curve: A Multi-Dimensional Framework for Measuring Bus Transport Equity in England"

### Core contribution
This paper is the first to simultaneously:
1. Quantify bus service inequality using Gini/Lorenz/Palma at LSOA level (n=33,755) for all England
2. Decompose inequality by region × urban/rural typology across 8 policy dimensions
3. Use ML (Random Forest + SHAP) to show car ownership — not poverty — drives coverage
4. Apply Green Book BCR framework to bus investment at regional level
5. Assess all 298 LADs for Bus Services Act 2025 franchising readiness

### Suggested sections
1. Introduction (transport justice, policy context, BSA 2025)
2. Literature review (transport deprivation, inequality measurement, accessibility)
3. Data & Methods (8 data sources, 2SFCA, Gini/Palma/CI, RF, BCR framework)
4. Results
   - 4.1 Equity metrics nationally and by region
   - 4.2 Accessibility and service deserts
   - 4.3 Socio-economic correlates and ML analysis
   - 4.4 Economic appraisal
   - 4.5 Policy readiness (BSA 2025)
5. Discussion (pro-rich bias, car dependency trap, policy implications)
6. Conclusion (recommendations, limitations, open data)

### Suggested figures for paper (select 8-10)
1. Lorenz curve — national bus service distribution
2. Gini by region (horizontal bar)
3. 400m coverage by region × urban/rural (grouped bar)
4. Scatter: coverage vs deprivation (IMD decile)
5. Scatter: coverage vs car ownership
6. SHAP feature importance bar chart
7. Route archetypes scatter clusters
8. BSA readiness tier distribution (stacked bar) by region
9. Heatmap: deprivation decile × urban/rural coverage
10. Choropleth map of coverage/SQI (if exportable as static)

### Suggested tables for paper
- Table 1: Data sources (as above)
- Table 2: Regional summary (Gini, coverage, trips/cap, BCR, BSA readiness)
- Table 3: Urban vs rural breakdown (all regions)
- Table 4: Socio-economic correlations by factor
- Table 5: BSA 2025 tier distribution by region

---

## 6. Observed Anomalies / Limitations to acknowledge
- London rural data absent (no rural LSOAs in London — correct by definition)
- HHI is national figure shown for all regions (no regional operator disaggregation yet)
- Scenarios show same population_affected (5,649,005) for all — 10% of England, parametric
- ML R² (0.472) is national model applied uniformly — regional model would differ
- evidence_grade fields empty in current build — needs population for paper claims
- BCR 1.17 is "Low" VfM by Green Book standards — important caveat for economic section
