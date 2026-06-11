"""InsightEngine orchestrator — deterministic narrative generation.

Wires together: context resolver → rules → Jinja2 templates → JSON output.
No LLM calls. All insights are evidence-gated: rules suppress rather than mislead.
"""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

from aequitas.intelligence.context import AnalysisScope, resolve_context
from aequitas.intelligence.rules import RankingRule

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Mapping from section_id to template filename
_SECTION_TEMPLATES: dict[str, str] = {
    # Existing (kept for backward compat)
    "coverage_density": "coverage_density.j2",
    "equity": "equity.j2",
    "correlation": "correlation.j2",
    "ranking": "ranking.j2",
    "single_region": "single_region.j2",
    "gap_to_target": "gap_to_target.j2",
    "policy_scenario": "policy_scenario.j2",
    # Category A: Coverage & Accessibility
    "a1_route_density": "ranking.j2",
    "a2_stop_density": "ranking.j2",
    "a3_walking_distance": "coverage_gap.j2",
    "a4_coverage_equity": "equity.j2",
    "a5_service_deserts": "desert_spotlight.j2",
    "a6_urban_rural_gap": "urban_rural_gap.j2",
    "a7_investment_gap": "gap_to_target.j2",
    "a8_coverage_prediction": "ml_prediction.j2",
    # Category B: Service Quality
    "b1_frequency": "ranking.j2",
    "b2_operating_hours": "service_hours.j2",
    "b3_weekend_penalty": "weekend_penalty.j2",
    "b4_route_frequency": "route_frequency_ranking.j2",
    "b5_frequency_deprivation": "correlation.j2",
    # Category C: Route Characteristics
    "c1_route_length": "distribution.j2",
    "c2_stops_per_route": "distribution.j2",
    "c3_operator_hhi": "market_concentration.j2",
    "c4_urban_rural_routes": "urban_rural_gap.j2",
    "c5_length_vs_frequency": "correlation.j2",
    "c6_route_archetypes": "ml_clusters.j2",
    "c7_network_topology": "network_topology.j2",
    # Category D: Socio-Economic Correlations
    "d1_coverage_deprivation": "correlation.j2",
    "d2_coverage_unemployment": "correlation.j2",
    "d3_coverage_car": "correlation.j2",
    "d4_coverage_elderly": "correlation.j2",
    "d5_coverage_income": "correlation.j2",
    "d6_transport_poverty": "ml_clusters.j2",
    "d7_deprivation_urban_rural": "heatmap.j2",
    "d8_feature_importance": "ml_prediction.j2",
    # Category F: Equity & Social Inclusion
    "f1_gini": "equity.j2",
    "f2_disparity_ratio": "equity_decile.j2",
    "f3_ethnic_access": "correlation.j2",
    "f4_gender_accessibility": "accessibility_gap.j2",
    "f5_rural_penalty": "urban_rural_gap.j2",
    "f6_equitable_regions": "ranking.j2",
    # Category G: ML Insights
    "g1_route_clusters": "ml_clusters.j2",
    "g2_anomalies": "anomaly_spotlight.j2",
    "g3_coverage_model": "ml_prediction.j2",
    "g4_shap": "ml_prediction.j2",
    "g5_scenario_model": "policy_scenario.j2",
    # Category J: Economic Impact & BCR
    "j1_economic_value": "economic_value.j2",
    "j2_bcr": "bcr_analysis.j2",
    "j3_carbon": "carbon_reduction.j2",
    "j4_investment_priority": "ranking.j2",
    # Category BSA: Bus Services Act 2025
    "bsa1_franchising_readiness": "ranking.j2",
    "bsa2_operator_concentration": "market_concentration.j2",
    "bsa3_tier_distribution": "tier_distribution.j2",
    # Category PS: Policy Scenario Modelling
    "ps1_freq_restoration": "policy_scenario.j2",
    "ps2_evening_extension": "policy_scenario.j2",
    "ps3_drt_rural": "policy_scenario.j2",
    "ps4_franchise": "policy_scenario.j2",
    "ps5_scenario_comparison": "scenario_comparison.j2",
}


class InsightEngine:
    """Deterministic narrative generator for policy intelligence sections.

    Usage::

        engine = InsightEngine()
        result = engine.generate(
            section_id="coverage_density",
            region="all",
            urban_rural="all",
            stats={...},
        )
        # result["narrative"] contains the rendered text
    """

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(disabled_extensions=("j2",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._env.filters["format_thousands"] = lambda v: f"{int(v):,}"

    def generate(
        self,
        section_id: str,
        region: str = "all",
        urban_rural: str = "all",
        stats: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a narrative section for the given filter combination.

        Args:
            section_id: Identifier for the template to use (e.g. "coverage_density").
            region: ONS region code or "all".
            urban_rural: "all", "urban", or "rural".
            stats: Precomputed statistics dict passed as template context.

        Returns:
            Dict with keys:
            - "narrative": rendered markdown string (empty string if suppressed)
            - "section_id": echoed section identifier
            - "scope": analysis scope name
            - "suppressed": True if no evidence to render
        """
        ctx = resolve_context(region=region, urban_rural=urban_rural)
        stats = stats or {}

        # Determine if ranking data is present and rules permit
        ranking_rule = RankingRule()
        n_groups = 9 if ctx.scope == AnalysisScope.ALL_REGIONS else 1
        has_ranking = ranking_rule.should_fire(ctx, n_groups)

        template_name = _SECTION_TEMPLATES.get(section_id)

        # Shape-based override: a ranking-family section viewed for a single
        # region gets single_region stats (region_name/value/national_avg,
        # no best/worst) rather than a best/worst ranking — render with
        # single_region.j2 instead. See ISSUES.md §2.4/§8.1.
        if (
            template_name == "ranking.j2"
            and stats
            and "region_name" in stats
            and "value" in stats
            and "national_avg" in stats
            and "best" not in stats
            and "worst" not in stats
        ):
            template_name = "single_region.j2"

        narrative = ""
        suppressed = False

        if template_name is None:
            suppressed = True
        elif not stats:
            # No stats provided — suppress rather than render empty template
            suppressed = True
        elif section_id == "coverage_density" and not has_ranking and ctx.scope != AnalysisScope.SINGLE_REGION:
            # Subset scope with no ranking → suppress rankings
            suppressed = True
        else:
            try:
                template = self._env.get_template(template_name)
                narrative = template.render(**stats).strip()
            except Exception as exc:
                logger.warning(f"Narrative generation failed for {section_id}: {exc}")
                suppressed = True
                narrative = ""

        return {
            "narrative": narrative,
            "section_id": section_id,
            "scope": ctx.scope.value,
            "suppressed": suppressed,
        }
