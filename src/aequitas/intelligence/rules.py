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
