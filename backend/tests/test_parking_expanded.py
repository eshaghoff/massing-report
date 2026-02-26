"""Tests for expanded parking rules: accessible, bicycle, loading."""

from __future__ import annotations

import pytest

from app.zoning_engine.parking import (
    get_accessible_spaces,
    calculate_bicycle_parking,
    calculate_loading_berths,
    calculate_parking,
)


class TestAccessibleParking:
    """Test ADA accessible space calculations."""

    def test_small_lot_1_space(self):
        assert get_accessible_spaces(10) == 1

    def test_25_spaces(self):
        assert get_accessible_spaces(25) == 1

    def test_50_spaces(self):
        assert get_accessible_spaces(50) == 2

    def test_100_spaces(self):
        assert get_accessible_spaces(100) == 4

    def test_500_spaces(self):
        assert get_accessible_spaces(500) == 9

    def test_zero_spaces(self):
        assert get_accessible_spaces(0) == 0

    def test_large_lot(self):
        spaces = get_accessible_spaces(1500)
        assert spaces == 25  # 20 + (1500-1000)//100 = 25


class TestBicycleParking:
    """Test bicycle parking calculations (ZR 25-80)."""

    def test_residential_1_per_unit(self):
        result = calculate_bicycle_parking(unit_count=50)
        assert result["residential_bike_spaces"] == 50

    def test_residential_above_200(self):
        result = calculate_bicycle_parking(unit_count=300)
        # First 200: 200 spaces. Next 100: 50 spaces. Total = 250
        assert result["residential_bike_spaces"] == 250

    def test_commercial_bike_spaces(self):
        result = calculate_bicycle_parking(commercial_sf=50000)
        assert result["commercial_bike_spaces"] >= 1

    def test_bike_room_sf_calculated(self):
        result = calculate_bicycle_parking(unit_count=100)
        assert result["bike_room_sf"] > 0

    def test_total_combines_all(self):
        result = calculate_bicycle_parking(
            unit_count=50, commercial_sf=20000, cf_sf=10000
        )
        assert result["total_bike_spaces"] >= 50


class TestLoadingBerths:
    """Test loading berth calculations (ZR 36-60)."""

    def test_small_residential_no_berths(self):
        result = calculate_loading_berths(residential_sf=20000)
        assert result["residential_berths"] == 0

    def test_large_residential_1_berth(self):
        result = calculate_loading_berths(residential_sf=120000)
        assert result["residential_berths"] == 1

    def test_large_commercial_retail(self):
        result = calculate_loading_berths(commercial_sf=50000)
        assert result["commercial_berths"] >= 2

    def test_total_berths_sum(self):
        result = calculate_loading_berths(
            residential_sf=150000, commercial_sf=30000
        )
        assert result["total_berths"] == result["residential_berths"] + result["commercial_berths"] + result["cf_berths"]

    def test_loading_sf_calculated(self):
        result = calculate_loading_berths(residential_sf=500000)
        assert result["total_loading_sf"] > 0


class TestComprehensiveParking:
    """Test the full calculate_parking function with new fields."""

    def test_accessible_spaces_included(self):
        result = calculate_parking(
            district="R7A", unit_count=100, lot_area=20000, borough=3
        )
        assert "accessible_spaces_required" in result
        assert result["accessible_spaces_required"] > 0

    def test_transit_zone_flag(self):
        result = calculate_parking(
            district="R7A", unit_count=100, lot_area=20000, borough=1
        )
        assert result["in_transit_zone"] is True

    def test_bicycle_parking_included(self):
        result = calculate_parking(
            district="R7A", unit_count=100, lot_area=20000
        )
        assert "bicycle_parking" in result
        assert result["bicycle_parking"]["total_bike_spaces"] > 0

    def test_loading_berths_included(self):
        result = calculate_parking(
            district="R7A", unit_count=200, lot_area=20000
        )
        assert "loading_berths" in result

    def test_ten_unit_waiver(self):
        result = calculate_parking(
            district="R8A", unit_count=8, lot_area=20000, borough=3
        )
        assert result["waiver_eligible"] is True
