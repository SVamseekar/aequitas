# Insight Engine - Dynamic Narrative Generation System

## Status: IN PROGRESS (Day 3, Task 1.4 Extended)

**Decision:** Implement full Insight Engine to avoid hardcoding narratives across 50+ sections

## Architecture (5 Layers)

### ✅ Layer 1: Context Resolver (`context.py`) - COMPLETE
- `ViewContext` dataclass
- `resolve_context()` - Detects filter state
- `data_sufficient()` - Checks data quality thresholds

**Fixes:** Single-region "best/worst" bug

### ✅ Layer 2: Centralized Calculators (`calc.py`) - COMPLETE
- TAG 2024 constants (time values, carbon, BCR bands)
- `calculate_rank_and_distance()` - Rankings vs national avg
- `describe_distribution()` - Stats, outliers, CV
- `calculate_gap_to_target()` - Investment gap analysis
- `calculate_investment_requirement()` - NPV with discounting
- `calculate_bcr()` - Simplified BCR (delegates to full calculator)
- `calculate_correlation()` - Pearson r with significance tests
- `calculate_gini_coefficient()` - Equity metrics

**Fixes:** All hardcoded numbers (£42M, BCR 2.1, correlations)

### ✅ Layer 3: Metric Config (`config.py`) - COMPLETE
- `MetricConfig` dataclass for section definitions

### ⏳ Layer 4: Insight Rules (`rules.py`) - TODO
Need to implement:
- `InsightRule` protocol
- `INSIGHT_REGISTRY` - Rule registration system
- Core rules:
  - `RankingRule` - For all-regions comparisons
  - `SingleRegionPositioningRule` - For filtered views
  - `CorrelationRule` - For socio-economic analysis
  - `OutlierRule` - Calls out anomalies
  - `GapToInvestmentRule` - Calculates costs + BCR

### ⏳ Layer 5: Template Renderer (`templates.py`) - TODO
- Jinja2 templates for each context type
- Consulting-tone text blocks
- Dynamic value injection

### ⏳ Orchestrator (`engine.py`) - TODO
- `InsightEngine` class
- `run()` method that coordinates all layers

## Next Steps

1. **Complete rules.py** (~1.5 hours)
2. **Complete templates.py** (~1 hour)
3. **Complete engine.py** (~30 min)
4. **Refactor Category A** to use engine (~1 hour)
5. **Write tests** (~1 hour)

**Total remaining:** ~5 hours

## Usage Example (Once Complete)

```python
from dashboard.utils.insight_engine import InsightEngine, MetricConfig

# Define metric
config = MetricConfig(
    id='routes_per_100k',
    groupby='region_name',
    value_col='routes_per_100k',
    unit='routes per 100,000 population',
    sources=['NaPTAN Oct 2025', 'BODS', 'ONS 2021', 'TAG 2024'],
    rules=['ranking', 'single_region_positioning', 'gap_to_investment']
)

# Generate narrative
engine = InsightEngine()
result = engine.run(df, config, filters={'region': 'West Midlands'})

# Result contains:
# - summary: Executive summary paragraph
# - key_finding: One critical insight
# - recommendation: Policy actions with costs/BCR
# - investment: Multi-year investment requirement
# - sources: Data sources list
# - evidence: All underlying numbers (for QA/export)
```

## Files Created

- ✅ `__init__.py` - Package exports
- ✅ `context.py` - ViewContext, resolve_context(), data_sufficient()
- ✅ `calc.py` - TAG 2024 constants + all calculators
- ✅ `config.py` - MetricConfig dataclass
- ⏳ `rules.py` - Insight rules (TODO)
- ⏳ `templates.py` - Jinja2 templates (TODO)
- ⏳ `engine.py` - InsightEngine orchestrator (TODO)
- ⏳ `tests/` - Unit and golden tests (TODO)

## Benefits

✅ **Zero hardcoded values** - All numbers computed dynamically
✅ **Context-aware** - Adapts to filters intelligently
✅ **Evidence-gated** - Only shows insights supported by data
✅ **Reusable** - DRY architecture for all 50 sections
✅ **Testable** - Unit tests for calcs, golden tests for narratives
✅ **Maintainable** - TAG values updated once, reflected everywhere

## Integration with Roadmap

This extends Task 1.4 from 8 hours to 12 hours but sets foundation for:
- Task 1.5: Complete Category A (6 sections use engine)
- Week 2+: All remaining categories use same engine
- Zero technical debt from hardcoded narratives
