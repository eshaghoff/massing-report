"""Tests for building type rules."""

from __future__ import annotations

import pytest

from app.zoning_engine.building_types import (
    get_building_type_for_district,
    get_building_type_rules,
    get_max_units_by_lot_area,
    get_max_units_by_du_factor,
    calculate_tower_footprint,
    DWELLING_UNIT_FACTOR,
)


class TestBuildingTypeClassification:
    """Test building type classification for each district."""

    def test_r1_is_detached(self):
        assert get_building_type_for_district("R1") == "detached"

    def test_r2_is_detached(self):
        assert get_building_type_for_district("R2") == "detached"

    def test_r3a_is_semi_detached(self):
        assert get_building_type_for_district("R3A") == "semi_detached"

    def test_r4b_is_attached(self):
        assert get_building_type_for_district("R4B") == "attached"

    def test_r7a_is_apartment(self):
        assert get_building_type_for_district("R7A") == "apartment"

    def test_r9_is_tower_on_base(self):
        assert get_building_type_for_district("R9") == "tower_on_base"

    def test_r10a_is_tower_on_base(self):
        assert get_building_type_for_district("R10A") == "tower_on_base"

    def test_c5_1_is_tower(self):
        assert get_building_type_for_district("C5-1") == "tower"

    def test_c6_4_is_tower_on_base(self):
        assert get_building_type_for_district("C6-4") == "tower_on_base"


class TestBuildingTypeRules:
    """Test building type rule details."""

    def test_detached_has_two_side_yards(self):
        rules = get_building_type_rules("R1")
        assert rules["required_side_yards"] == 2

    def test_semi_detached_has_one_side_yard(self):
        rules = get_building_type_rules("R3A")
        assert rules["required_side_yards"] == 1

    def test_attached_no_side_yards(self):
        rules = get_building_type_rules("R4B")
        assert rules["required_side_yards"] == 0

    def test_tower_has_coverage_limit(self):
        rules = get_building_type_rules("R10")
        assert "tower_coverage_max" in rules
        assert rules["tower_coverage_max"] == 40


class TestMaxUnitsByLotArea:
    """Test low-density unit count limits."""

    def test_r1_large_lot(self):
        # R1 requires 9500 SF per DU
        units = get_max_units_by_lot_area("R1", 19000)
        assert units == 2

    def test_r3_2_units(self):
        # R3-2 requires 1700 SF per DU
        units = get_max_units_by_lot_area("R3-2", 5100)
        assert units == 3

    def test_r7a_returns_none(self):
        # R7A uses FAR, not lot area per DU
        result = get_max_units_by_lot_area("R7A", 10000)
        assert result is None

    def test_r5_units(self):
        # R5 requires 680 SF per DU
        units = get_max_units_by_lot_area("R5", 3400)
        assert units == 5


class TestDwellingUnitFactor:
    """Test dwelling unit factor (ZR 23-52) for R6-R12 districts.

    max_du = max_residential_floor_area / 680
    Fractions >= 0.75 round up; fractions < 0.75 are dropped.
    """

    def test_du_factor_is_680(self):
        assert DWELLING_UNIT_FACTOR == 680

    def test_r6_basic(self):
        # 4400 / 680 = 6.47 -> 6 (fraction 0.47 < 0.75)
        assert get_max_units_by_du_factor("R6", 4400) == 6

    def test_r6_round_up(self):
        # 5950 / 680 = 8.75 -> 9 (fraction 0.75 >= 0.75, rounds up)
        assert get_max_units_by_du_factor("R6", 5950) == 9

    def test_r6_exact(self):
        # 6800 / 680 = 10.0 -> 10 (exact)
        assert get_max_units_by_du_factor("R6", 6800) == 10

    def test_r6_just_under_threshold(self):
        # 5100 / 680 = 7.50 -> 7 (fraction 0.50 < 0.75)
        assert get_max_units_by_du_factor("R6", 5100) == 7

    def test_r6_just_at_threshold(self):
        # 5610 / 680 = 8.25 -> 8 (fraction 0.25 < 0.75)
        assert get_max_units_by_du_factor("R6", 5610) == 8

    def test_r7a(self):
        # 20000 / 680 = 29.41 -> 29
        assert get_max_units_by_du_factor("R7A", 20000) == 29

    def test_r8a(self):
        # 30100 / 680 = 44.26 -> 44
        assert get_max_units_by_du_factor("R8A", 30100) == 44

    def test_r10(self):
        # 100000 / 680 = 147.06 -> 147
        assert get_max_units_by_du_factor("R10", 100000) == 147

    def test_r12(self):
        # 90000 / 680 = 132.35 -> 132
        assert get_max_units_by_du_factor("R12", 90000) == 132

    def test_r5_returns_none(self):
        # R5 uses lot area per DU, not DU factor
        assert get_max_units_by_du_factor("R5", 10000) is None

    def test_r3_returns_none(self):
        assert get_max_units_by_du_factor("R3-2", 5000) is None

    def test_r1_returns_none(self):
        assert get_max_units_by_du_factor("R1", 50000) is None

    def test_senior_housing_exempt(self):
        # Qualifying senior housing: no DU factor applies
        result = get_max_units_by_du_factor("R7A", 20000, is_senior_housing=True)
        assert result is None

    def test_conversion_exempt(self):
        # Conversions: no DU factor applies
        result = get_max_units_by_du_factor("R8", 50000, is_conversion=True)
        assert result is None

    def test_zero_floor_area(self):
        assert get_max_units_by_du_factor("R6", 0) == 0

    def test_minimum_one_unit(self):
        # Very small floor area: at least 1 unit
        assert get_max_units_by_du_factor("R6", 100) == 1

    def test_c6_districts_use_du_factor(self):
        # C6 commercial districts with residential equivalents
        result = get_max_units_by_du_factor("C6-2", 20000)
        assert result == 29  # 20000/680 = 29.41 -> 29


class TestTowerFootprint:
    """Test tower-on-base footprint calculations."""

    def test_r10_has_tower(self):
        result = calculate_tower_footprint(20000, "R10", 100, 200)
        assert result["is_tower"] is True
        assert result["tower_footprint_sf"] > 0
        assert result["base_footprint_sf"] > 0

    def test_r7a_no_tower(self):
        result = calculate_tower_footprint(10000, "R7A")
        assert result["is_tower"] is False

    def test_tower_coverage_under_40pct(self):
        result = calculate_tower_footprint(20000, "R10", 100, 200)
        assert result["tower_coverage_pct"] <= 40.1  # Allow small rounding
