"""Unit tests for refresh download helpers (no network)."""

from pathlib import Path

import pytest

from aequitas.ingestion.download import BODS_URLS, NAPTAN_URL, ONS_LSOA_PWC_CSV, require_disk

try:
    from aequitas.pipeline.refresh import launch_agent_plist
except ImportError:
    launch_agent_plist = None  # type: ignore[assignment,misc]


def test_official_urls_are_https() -> None:
    assert NAPTAN_URL.startswith("https://naptan.api.dft.gov.uk/")
    assert all(u.startswith("https://data.bus-data.dft.gov.uk/") for u in BODS_URLS)
    assert ONS_LSOA_PWC_CSV.startswith("https://open-geography-portalx-ons.hub.arcgis.com/")


def test_require_disk_fails_when_need_is_absurd(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Need"):
        require_disk(tmp_path, needed_gb=10_000_000)


@pytest.mark.skipif(launch_agent_plist is None, reason="refresh module not on this branch")
def test_launch_agent_plist_points_at_refresh(tmp_path: Path) -> None:
    xml = launch_agent_plist(tmp_path, "/opt/homebrew/bin/uv")
    assert "aequitas</string>" in xml
    assert "refresh</string>" in xml
    assert str(tmp_path) in xml
    assert "<key>Day</key>" in xml
