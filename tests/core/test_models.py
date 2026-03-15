"""Tests for core Pydantic v2 data models."""

import pytest
from pydantic import ValidationError
from aequitas.core.models import BusStop, Route, LSOARecord, RegionSummary


class TestBusStop:
    def test_valid_stop(self):
        stop = BusStop(
            stop_id="0100BRP90310",
            stop_name="High Street",
            latitude=51.5,
            longitude=-0.12,
            lsoa_code="E01000001",
            region_code="E12000007",
            stop_type="BCT",
        )
        assert stop.stop_id == "0100BRP90310"

    def test_rejects_wales_lsoa(self):
        with pytest.raises(ValidationError):
            BusStop(
                stop_id="0100BRP90310",
                stop_name="Test",
                latitude=51.5,
                longitude=-0.12,
                lsoa_code="W01000001",
                region_code="E12000007",
                stop_type="BCT",
            )

    def test_rejects_invalid_coords(self):
        with pytest.raises(ValidationError):
            BusStop(
                stop_id="0100BRP90310",
                stop_name="Test",
                latitude=70.0,
                longitude=-0.12,
                lsoa_code="E01000001",
                region_code="E12000007",
                stop_type="BCT",
            )


class TestRoute:
    def test_valid_route(self):
        route = Route(
            route_id="R001",
            line_name="1A",
            route_length_km=15.2,
            num_stops=25,
            trips_per_day=48,
            regions_served=["E12000007"],
            has_geometry=True,
        )
        assert route.route_id == "R001"

    def test_negative_length_rejected(self):
        with pytest.raises(ValidationError):
            Route(
                route_id="R001",
                line_name="1A",
                route_length_km=-5.0,
                num_stops=25,
                trips_per_day=48,
                regions_served=["E12000007"],
                has_geometry=True,
            )


class TestRegionSummary:
    def test_stops_per_1000_sanity(self):
        """Sanity validator: stops_per_1000 > 30 means counting error."""
        with pytest.raises(ValidationError, match="sanity"):
            RegionSummary(
                region_code="E12000001",
                region_name="North East",
                population=2_647_000,
                unique_stops=100_000,
                unique_routes=500,
                stops_per_1000=37.8,
                routes_per_100k=18.9,
            )

    def test_valid_summary(self):
        s = RegionSummary(
            region_code="E12000001",
            region_name="North East",
            population=2_647_000,
            unique_stops=18_000,
            unique_routes=500,
            stops_per_1000=6.8,
            routes_per_100k=18.9,
        )
        assert s.population == 2_647_000
