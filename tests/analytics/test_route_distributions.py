"""c1/c2 histograms from GTFS. Missing shapes omit length only."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from aequitas.analytics.route_distributions import LENGTH_OMIT, network_charts
from aequitas.france.network import load_nap_network
from aequitas.netherlands.network import load_ovapi_network


def _write(path: Path, files: dict[str, str]) -> None:
    with ZipFile(path, "w") as zf:
        for name, body in files.items():
            zf.writestr(name, body)


def _feed(*, route_type: str, route_id: str = "R1", stops: list[str] | None = None) -> dict[str, str]:
    stop_ids = stops or ["S1", "S2", "S3"]
    stop_rows = "\n".join(f"T1,{sid}" for sid in stop_ids)
    return {
        "agency.txt": "agency_id,agency_name\nA,Agency\n",
        "routes.txt": f"route_id,agency_id,route_type\n{route_id},A,{route_type}\n",
        "trips.txt": f"trip_id,route_id\nT1,{route_id}\n",
        "stop_times.txt": f"trip_id,stop_id\n{stop_rows}\n",
    }


def test_missing_shapes_omits_length_and_keeps_stops(tmp_path: Path) -> None:
    zp = tmp_path / "ovapi.zip"
    _write(zp, _feed(route_type="3", stops=["S1", "S2", "S3", "S4"]))
    bus = load_ovapi_network(zp, mode="bus")
    assert bus["route_length_km"] is None
    assert bus["stops_per_route"] == [4]
    c1, c2 = network_charts(
        bus,
        place="the Netherlands",
        length_title="Route length — {place}",
        stops_title="Stops per route — {place}",
    )
    assert c1["type"] == "histogram"
    assert c1["empty_reason"] == LENGTH_OMIT
    assert c1["data"] == []
    assert c2["type"] == "histogram"
    assert "empty_reason" not in c2
    assert c2["n"] == 1
    assert c2["data"][0]["value"] == 1
    assert sum(row["value"] for row in c2["data"]) == 1


def test_nl_mode_bus_excludes_rail(tmp_path: Path) -> None:
    zp = tmp_path / "ovapi.zip"
    files = _feed(route_type="3", route_id="BUS", stops=["S1", "S2"])
    files["routes.txt"] += "RAIL,A,2\n"
    files["trips.txt"] += "T2,RAIL\n"
    files["stop_times.txt"] += "T2,S9\nT2,S8\nT2,S7\nT2,S6\nT2,S5\n"
    _write(zp, files)
    bus = load_ovapi_network(zp, mode="bus")
    all_pt = load_ovapi_network(zp, mode="all")
    assert bus["stops_per_route"] == [2]
    assert sorted(all_pt["stops_per_route"]) == [2, 5]
    assert bus["n_routes"] == 1
    assert all_pt["n_routes"] == 2


def test_france_prefixes_dataset_id_so_route_ids_do_not_merge(tmp_path: Path) -> None:
    folder = tmp_path / "nap"
    folder.mkdir()
    _write(folder / "111.zip", _feed(route_type="3", stops=["A", "B"]))
    _write(folder / "222.zip", _feed(route_type="3", stops=["C", "D", "E", "F"]))
    packed = load_nap_network(folder, mode="bus")
    assert packed["route_length_km"] is None
    assert sorted(packed["stops_per_route"]) == [2, 4]
    assert packed["n_routes"] == 2
    c1, c2 = network_charts(
        packed,
        place="France",
        length_title="Route length — {place}",
        stops_title="Stops per NAP route — {place}",
    )
    assert c1["empty_reason"] == LENGTH_OMIT
    assert c2["type"] == "histogram"
    assert c2["n"] == 2
    assert len(c2["data"]) <= 6
    assert c2["type"] != "kpi_tiles"
