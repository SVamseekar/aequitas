from datetime import datetime, timedelta, timezone
import json

from aequitas.pipeline.refresh import last_success_age_days, run_refresh


def test_min_interval_skips(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    stamp = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    (data / "refresh_state.json").write_text(
        json.dumps({"status": "ok", "finished_at": stamp}),
        encoding="utf-8",
    )

    class Cfg:
        project_root = tmp_path
        force_full_network = False
        warehouse_path = tmp_path / "missing.duckdb"
        raw_dir = tmp_path / "raw"
        processed_dir = tmp_path / "processed"
        audit_dir = tmp_path / "audit"

    monkeypatch.setattr("aequitas.pipeline.refresh.PipelineConfig", lambda: Cfg())
    assert run_refresh(min_interval_days=25) == 0
    assert last_success_age_days(tmp_path) is not None
    assert last_success_age_days(tmp_path) < 25
