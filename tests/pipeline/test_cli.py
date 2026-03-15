"""Tests for pipeline CLI."""

from click.testing import CliRunner
from aequitas.pipeline.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "pipeline" in result.output.lower()


def test_cli_ingest_help():
    runner = CliRunner()
    result = runner.invoke(main, ["ingest", "--help"])
    assert result.exit_code == 0


def test_cli_validate_stage():
    runner = CliRunner()
    result = runner.invoke(main, ["validate"])
    # Should run validation gates against Phase 0 audit Parquets
    assert result.exit_code == 0


def test_cli_all_commands_present():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    output = result.output
    for cmd in ["ingest", "process", "analytics", "intelligence", "warehouse", "validate", "run"]:
        assert cmd in output, f"Command '{cmd}' not found in help output"
