"""Validation report generator — human-readable + JSON output.

Converts validate_against_ground_truth() results into a readable report.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


def generate_report(validation_result: dict[str, Any], output_path: Path | None = None) -> str:
    """Generate a human-readable validation report from check results.

    Args:
        validation_result: Output from validate_against_ground_truth().
        output_path: Optional path to write the report to disk.

    Returns:
        Report as a markdown-formatted string.
    """
    checks = validation_result.get("checks", [])
    n_pass = validation_result.get("n_pass", 0)
    n_warn = validation_result.get("n_warn", 0)
    n_fail = validation_result.get("n_fail", 0)
    all_pass = validation_result.get("all_pass", False)

    lines = [
        f"# Aequitas Pipeline Validation Report",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Status:** {'✅ ALL PASS' if all_pass else f'❌ {n_fail} FAILED'}",
        f"**Checks:** {n_pass} PASS / {n_warn} WARN / {n_fail} FAIL",
        "",
        "## Checks",
        "",
    ]

    for check in checks:
        status_icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(check["status"], "?")
        lines.append(
            f"- {status_icon} **{check['name']}**: "
            f"expected `{check['expected']}`, "
            f"got `{check['actual']}` "
            f"(tolerance: {check['tolerance']})"
        )

    report = "\n".join(lines)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report)
        logger.info(f"Validation report written to {output_path}")

    return report
