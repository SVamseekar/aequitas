"""Evidence-gated rules for InsightEngine.

Key principle: suppress > mislead.
A rule that doesn't fire produces no output — never a wrong insight.

Rules:
- RankingRule: fire when n_groups ≥ 3 (rankings only valid with multiple groups)
- SingleRegionRule: fire only for SINGLE_REGION scope
- CorrelationRule: fire when n ≥ 30 and p_value < 0.05
- GiniEquityRule: fire when n ≥ 100 LSOA observations
- GapToInvestmentRule: fire when at least one unit is below target
"""

from aequitas.intelligence.context import AnalysisContext, AnalysisScope


class RankingRule:
    """Fire when there are enough groups to produce a meaningful ranking.

    Requires n_groups ≥ 3 AND scope is ALL_REGIONS.
    """

    MIN_GROUPS = 3

    def should_fire(self, ctx: AnalysisContext, n_groups: int) -> bool:
        """Return True if ranking insight should be generated.

        Args:
            ctx: Resolved analysis context.
            n_groups: Number of comparison groups available.

        Returns:
            True only when scope is ALL_REGIONS and n_groups ≥ 3.
        """
        return ctx.scope == AnalysisScope.ALL_REGIONS and n_groups >= self.MIN_GROUPS


class SingleRegionRule:
    """Fire only for SINGLE_REGION scope — compares one region to national average."""

    def should_fire(self, ctx: AnalysisContext) -> bool:
        """Return True if single-region comparison should be generated."""
        return ctx.scope == AnalysisScope.SINGLE_REGION


class CorrelationRule:
    """Fire when sample is large enough and correlation is statistically significant.

    Requires n ≥ 30 and p_value < 0.05.
    """

    MIN_N = 30
    SIGNIFICANCE_THRESHOLD = 0.05

    def should_fire(self, n: int, p_value: float) -> bool:
        """Return True if correlation insight is reliable enough to report.

        Args:
            n: Sample size used in correlation.
            p_value: Two-tailed p-value from Pearson test.

        Returns:
            True when n ≥ 30 and p < 0.05.
        """
        return n >= self.MIN_N and p_value < self.SIGNIFICANCE_THRESHOLD


class GiniEquityRule:
    """Fire when the equity analysis has sufficient LSOA observations."""

    MIN_LSOAS = 100

    def should_fire(self, n_lsoas: int) -> bool:
        """Return True when enough LSOAs are available for Gini/Lorenz analysis.

        Args:
            n_lsoas: Number of LSOA records in the analysis set.

        Returns:
            True when n_lsoas ≥ 100.
        """
        return n_lsoas >= self.MIN_LSOAS


class GapToInvestmentRule:
    """Fire when at least one geographic unit falls below the investment target."""

    def should_fire(self, n_below_target: int) -> bool:
        """Return True when there are units requiring investment to reach target.

        Args:
            n_below_target: Number of LSOAs/LADs below the target service level.

        Returns:
            True when n_below_target > 0.
        """
        return n_below_target > 0


class MinLsoaRule:
    """Fire when enough LSOAs are available for meaningful analysis."""

    MIN_LSOAS = 100

    def should_fire(self, n_lsoas: int) -> bool:
        """Return True when n_lsoas >= 100."""
        return n_lsoas >= self.MIN_LSOAS


class DesertRule:
    """Fire when at least one service desert LSOA exists."""

    def should_fire(self, n_desert_lsoas: int) -> bool:
        """Return True when any desert LSOAs exist."""
        return n_desert_lsoas >= 1


class UrbanRuralRule:
    """Fire when both urban and rural groups have sufficient sample size."""

    MIN_PER_GROUP = 30

    def should_fire(self, n_urban: int, n_rural: int) -> bool:
        """Return True when both urban and rural groups meet minimum size."""
        return n_urban >= self.MIN_PER_GROUP and n_rural >= self.MIN_PER_GROUP


class MLPredictionRule:
    """Fire when ML model has positive explanatory power with enough features."""

    MIN_FEATURES = 3

    def should_fire(self, r2: float, n_features: int) -> bool:
        """Return True when R² > 0 and at least MIN_FEATURES are available."""
        return r2 > 0 and n_features >= self.MIN_FEATURES


class DistributionRule:
    """Fire when sample size is sufficient for distribution summary."""

    MIN_N = 30

    def should_fire(self, n: int) -> bool:
        """Return True when n >= 30."""
        return n >= self.MIN_N


class MarketConcentrationRule:
    """Fire when there are enough operators to compute HHI meaningfully."""

    MIN_OPERATORS = 2

    def should_fire(self, n_operators: int) -> bool:
        """Return True when at least 2 operators exist."""
        return n_operators >= self.MIN_OPERATORS


class ClusterRule:
    """Fire when clustering produced at least 2 distinct groups."""

    MIN_CLUSTERS = 2

    def should_fire(self, n_clusters: int) -> bool:
        """Return True when at least 2 clusters exist."""
        return n_clusters >= self.MIN_CLUSTERS


class NetworkRule:
    """Fire when enough routes exist for network topology analysis."""

    MIN_ROUTES = 10

    def should_fire(self, n_routes: int) -> bool:
        """Return True when at least 10 routes exist."""
        return n_routes >= self.MIN_ROUTES


class HeatmapRule:
    """Fire when every cell in the heatmap has enough observations."""

    MIN_CELL_N = 10

    def should_fire(self, min_cell_n: int) -> bool:
        """Return True when the smallest cell has >= 10 observations."""
        return min_cell_n >= self.MIN_CELL_N


class DecileRule:
    """Fire when all 10 IMD deciles have enough LSOAs for comparison."""

    MIN_PER_DECILE = 100

    def should_fire(self, decile_counts: list[int]) -> bool:
        """Return True when all 10 deciles have >= 100 LSOAs each."""
        return len(decile_counts) == 10 and all(c >= self.MIN_PER_DECILE for c in decile_counts)


class DemographicRule:
    """Fire when every demographic group has enough observations."""

    MIN_PER_GROUP = 30

    def should_fire(self, group_counts: list[int]) -> bool:
        """Return True when all groups meet the minimum count."""
        return all(c >= self.MIN_PER_GROUP for c in group_counts)


class AccessibilityRule:
    """Fire when enough POIs exist for accessibility gap analysis."""

    MIN_POIS = 10

    def should_fire(self, n_pois: int) -> bool:
        """Return True when at least 10 POIs are present."""
        return n_pois >= self.MIN_POIS


class AnomalyRule:
    """Fire when enough anomalies are detected to report patterns."""

    MIN_ANOMALIES = 10

    def should_fire(self, n_anomalies: int) -> bool:
        """Return True when at least 10 anomalies detected."""
        return n_anomalies >= self.MIN_ANOMALIES


class CarbonRule:
    """Fire when modal shift produces positive CO2 savings."""

    def should_fire(self, co2_saving: float) -> bool:
        """Return True when CO2 saving is strictly positive."""
        return co2_saving > 0


class TierRule:
    """Fire when enough LADs are assessed for tier distribution."""

    MIN_LADS = 10

    def should_fire(self, n_lads: int) -> bool:
        """Return True when at least 10 LADs are assessed."""
        return n_lads >= self.MIN_LADS


class ScenarioComparisonRule:
    """Fire when multiple scenarios exist for comparison."""

    MIN_SCENARIOS = 2

    def should_fire(self, n_scenarios: int) -> bool:
        """Return True when at least 2 scenarios exist."""
        return n_scenarios >= self.MIN_SCENARIOS
