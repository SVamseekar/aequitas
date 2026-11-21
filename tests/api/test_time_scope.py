"""Missing regional snapshots never borrow a registered national observation."""
from pathlib import Path

import pytest

from aequitas.api.routers import time_series


@pytest.mark.parametrize('has_warehouse', [True, False])
def test_regional_unavailable_does_not_substitute_national(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, has_warehouse: bool,
) -> None:
    warehouse = tmp_path / 'dated.duckdb'
    if has_warehouse:
        warehouse.touch()
    monkeypatch.setattr(time_series, 'list_packs', lambda country: [{
        'pack_id': '2026-08-01', 'as_of': '2026-08-01', 'current': True,
        'warehouse': str(warehouse), 'score': 80, 'n_areas': 33755,
    }])
    monkeypatch.setattr(time_series, 'resolve_pack', lambda *args: {'pack_id': '2026-08-01'})

    def unavailable(*args: object, **kwargs: object) -> dict:
        raise RuntimeError('Regional snapshot unavailable')

    monkeypatch.setattr(time_series, 'extract_metrics', unavailable)
    payload = time_series.get_time_series(
        country='england', region='E12000002', urban_rural='all', metric='score',
        pack=None, as_of=None,
    )
    assert payload['points'][0]['value'] is None
    assert payload['points'][0]['n_areas'] is None
