"""Tests for parking calculator."""

from __future__ import annotations

import pytest

from app.zoning_engine.parking import calculate_parking


class TestParkingRatios:
    """Test parking requirement calculations."""

    def test_r1_one_per_unit(self):
        result = calculate_parking("R1", unit_count=10, lot_area=5000, borough=5)
        assert result["residential_spaces_required"] == 10

    def test_r7a_half_per_unit(self):
        result = calculate_parking("R7A", unit_count=20, lot_area=5000, borough=3)
        assert result["residential_spaces_required"] == 10

    def test_r10_low_ratio(self):
        result = calculate_parking("R10", unit_count=100, lot_area=50000, borough=1)
        # Manhattan = transit zone, R10 gets 0 parking
        assert result["residential_spaces_required"] == 0


class TestTransitZone:
    """Test transit zone waivers."""

    def test_manhattan_is_transit_zone(self):
        result = calculate_parking("R7A", unit_count=20, lot_area=5000, borough=1)
        # Manhattan reduces parking significantly
        assert result["residential_spaces_required"] < 10

    def test_staten_island_not_transit_zone(self):
        result = calculate_parking("R7A", unit_count=20, lot_area=5000, borough=5)
        assert result["residential_spaces_required"] == 10


class TestSmallLotWaiver:
    """Test small lot parking waivers."""

    def test_r6_small_lot_waiver(self):
        result = calculate_parking("R6", unit_count=5, lot_area=5000, borough=3)
        assert result["waiver_eligible"] is True

    def test_r6_large_lot_no_waiver(self):
        result = calculate_parking("R6", unit_count=50, lot_area=20000, borough=3)
        assert result["waiver_eligible"] is False


class TestCommercialParking:
    """Test commercial use parking."""

    def test_commercial_parking(self):
        result = calculate_parking(
            "R7A", unit_count=0, commercial_sf=10000,
            lot_area=5000, borough=3,
        )
        assert result["commercial_spaces_required"] > 0

    def test_manhattan_no_commercial_parking(self):
        result = calculate_parking(
            "R7A", unit_count=0, commercial_sf=10000,
            lot_area=5000, borough=1,
        )
        assert result["commercial_spaces_required"] == 0


class TestParkingOptions:
    """Test parking layout options."""

    def test_options_generated_when_needed(self):
        result = calculate_parking("R7A", unit_count=20, lot_area=5000, borough=3)
        if result["total_spaces_required"] > 0:
            assert len(result["parking_options"]) > 0

    def test_no_options_when_zero_spaces(self):
        result = calculate_parking("R10", unit_count=5, lot_area=50000, borough=1)
        if result["total_spaces_required"] == 0:
            assert len(result["parking_options"]) == 0

    def test_below_grade_option_has_cost(self):
        result = calculate_parking("R7A", unit_count=20, lot_area=5000, borough=3)
        below_grade = next(
            (o for o in result["parking_options"] if o["type"] == "below_grade"),
            None,
        )
        if below_grade:
            assert below_grade["estimated_cost"] > 0
            assert below_grade["total_sf"] > 0
