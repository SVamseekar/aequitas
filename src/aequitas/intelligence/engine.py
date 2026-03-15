"""InsightEngine orchestrator — deterministic narrative generation.

Wires together: context resolver → rules → Jinja2 templates → JSON output.
No LLM calls. All insights are evidence-gated: rules suppress rather than mislead.
"""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from aequitas.intelligence.context import AnalysisScope, resolve_context
from aequitas.intelligence.rules import RankingRule

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Mapping from section_id to template filename
_SECTION_TEMPLATES: dict[str, str] = {
    "coverage_density": "coverage_density.j2",
    "equity": "equity.j2",
    "correlation": "correlation.j2",
    "ranking": "ranking.j2",
    "single_region": "single_region.j2",
    "gap_to_target": "gap_to_target.j2",
    "policy_scenario": "policy_scenario.j2",
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
            except Exception:
                suppressed = True
                narrative = ""

        return {
            "narrative": narrative,
            "section_id": section_id,
            "scope": ctx.scope.value,
            "suppressed": suppressed,
        }
