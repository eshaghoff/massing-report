"""Tests for City of Yes for Housing Opportunity provisions."""

from __future__ import annotations

import pytest

from app.zoning_engine.far_tables import (
    get_far_for_district,
    get_uap_far,
    get_uap_bonus_far,
    UAP_AFFORDABLE_FAR,
    RESIDENTIAL_FAR,
)
from app.zoning_engine.height_setback import get_height_rules
from app.zoning_engine.parking import calculate_parking, get_parking_zone
from app.zoning_engine.city_of_yes import (
    calculate_uap_scenario,
    is_adu_eligible,
    get_adu_rules,
    is_office_conversion_eligible,
    get_city_of_yes_summary,
)
from app.models.schemas import LotProfile
from app.zoning_engine.calculator import ZoningCalculator


calc = ZoningCalculator()


class TestUAPFARBonuses:
    """Test Universal Affordability Preference FAR values."""

    def test_r6a_uap_far(self):
        """R6A: base 3.0, UAP max 3.9."""
        assert get_uap_far("R6A") == 3.90

    def test_r7a_uap_far(self):
        """R7A: base 4.0, UAP max 5.01."""
        assert get_uap_far("R7A") == 5.01

    def test_r8a_uap_far(self):
        """R8A: base 6.02, UAP max 7.20."""
        assert get_uap_far("R8A") == 7.20

    def test_r9a_uap_far(self):
        """R9A: base 7.52, UAP max 9.02."""
        assert get_uap_far("R9A") == 9.02

    def test_r10a_uap_far(self):
        """R10A: base 10.0, UAP max 12.0."""
        assert get_uap_far("R10A") == 12.00

    def test_r11_uap_far(self):
        """R11: new district, UAP max 15.0."""
        assert get_uap_far("R11") == 15.00

    def test_r12_uap_far(self):
        """R12: new district, UAP max 18.0."""
        assert get_uap_far("R12") == 18.00

    def test_r1_no_uap(self):
        """Low density districts not eligible for UAP."""
        assert get_uap_far("R1") is None
        assert get_uap_far("R5") is None

    def test_uap_bonus_positive(self):
        """All UAP-eligible districts should have positive bonus."""
        for district in UAP_AFFORDABLE_FAR:
            bonus = get_uap_bonus_far(district)
            assert bonus is not None and bonus > 0, \
                f"UAP bonus for {district} should be positive"

    def test_uap_bonus_r6a(self):
        bonus = get_uap_bonus_far("R6A")
        assert bonus == pytest.approx(0.9, abs=0.01)

    def test_uap_bonus_r7a(self):
        bonus = get_uap_bonus_far("R7A")
        assert bonus == pytest.approx(1.01, abs=0.01)


class TestUAPHeightBonuses:
    """Test that UAP provides height bonuses."""

    def test_r7a_standard_vs_affordable_narrow(self):
        """R7A narrow: standard 75 ft, affordable should be higher."""
        standard = get_height_rules("R7A", "narrow", is_affordable=False)
        affordable = get_height_rules("R7A", "narrow", is_affordable=True)
        assert affordable["max_building_height"] > standard["max_building_height"]
        assert affordable["max_building_height"] == 95

    def test_r7a_standard_vs_affordable_wide(self):
        """R7A wide: standard 85 ft, affordable 115 ft."""
        standard = get_height_rules("R7A", "wide", is_affordable=False)
        affordable = get_height_rules("R7A", "wide", is_affordable=True)
        assert standard["max_building_height"] == 85
        assert affordable["max_building_height"] == 115

    def test_r6a_affordable_height(self):
        """R6A: affordable height bonus from 75 to 95."""
        standard = get_height_rules("R6A", "narrow", is_affordable=False)
        affordable = get_height_rules("R6A", "narrow", is_affordable=True)
        assert standard["max_building_height"] == 75
        assert affordable["max_building_height"] == 95

    def test_r4b_no_affordable_bonus(self):
        """R4B shouldn't have UAP height bonus."""
        standard = get_height_rules("R4B", "narrow", is_affordable=False)
        affordable = get_height_rules("R4B", "narrow", is_affordable=True)
        assert standard["max_building_height"] == affordable["max_building_height"]


class TestNewDistricts:
    """Test City of Yes new districts (R6D, R11, R12)."""

    def test_r6d_exists(self):
        far = get_far_for_district("R6D")
        assert far["residential"] == 2.50

    def test_r6d_uap(self):
        assert get_uap_far("R6D") == 3.00

    def test_r11_exists(self):
        far = get_far_for_district("R11")
        assert far["residential"] == 12.0

    def test_r12_exists(self):
        far = get_far_for_district("R12")
        assert far["residential"] == 15.0

    def test_r7d_corrected_far(self):
        """R7D FAR corrected to 4.66 (was 4.20)."""
        far = get_far_for_district("R7D")
        assert far["residential"] == 4.66


class TestParkingZones:
    """Test City of Yes four-zone parking system."""

    def test_manhattan_core_zone_0(self):
        """Manhattan CDs 1-8 are Zone 0."""
        assert get_parking_zone(1, 5) == 0  # CD 5 Manhattan

    def test_manhattan_upper_zone_1(self):
        """Upper Manhattan (CDs 9-12) is Zone 1."""
        assert get_parking_zone(1, 9) == 1

    def test_brooklyn_inner_transit(self):
        """Downtown Brooklyn (CD 2) is Inner Transit Zone."""
        assert get_parking_zone(3, 2) == 1

    def test_queens_inner_transit(self):
        """LIC (Queens CD 1) is Inner Transit Zone."""
        assert get_parking_zone(4, 1) == 1

    def test_queens_outer_transit(self):
        """Some Queens CDs are Outer Transit Zone."""
        assert get_parking_zone(4, 5) == 2

    def test_staten_island_beyond(self):
        """Most of Staten Island is Beyond Greater Transit Zone."""
        assert get_parking_zone(5, 3) == 3

    def test_zone_0_no_parking(self):
        """Manhattan Core: no residential parking required."""
        result = calculate_parking(
            "R7A", unit_count=100, lot_area=10000,
            borough=1, community_district=5,
        )
        assert result["residential_spaces_required"] == 0
        assert result["parking_zone"] == 0

    def test_zone_1_no_parking(self):
        """Inner Transit Zone: no residential parking required."""
        result = calculate_parking(
            "R7A", unit_count=100, lot_area=10000,
            borough=3, community_district=2,  # Downtown Brooklyn
        )
        assert result["residential_spaces_required"] == 0
        assert result["parking_zone"] == 1

    def test_zone_2_reduced_parking(self):
        """Outer Transit Zone: reduced parking with waivers."""
        result = calculate_parking(
            "R7A", unit_count=20, lot_area=10000,
            borough=4, community_district=5,  # Outer Queens
        )
        # Should be reduced from standard 0.50 ratio
        assert result["parking_zone"] == 2
        # 20 units * 0.25 = 5 spaces, but waiver threshold is 15, so 0
        assert result["residential_spaces_required"] == 0

    def test_zone_3_standard_parking(self):
        """Beyond Greater Transit Zone: standard requirements."""
        result = calculate_parking(
            "R7A", unit_count=20, lot_area=10000,
            borough=5, community_district=3,  # Staten Island
        )
        assert result["parking_zone"] == 3
        assert result["residential_spaces_required"] == 10  # 20 * 0.50

    def test_affordable_units_no_parking(self):
        """Affordable units should have no parking requirement under CoY."""
        result = calculate_parking(
            "R7A", unit_count=100, affordable_units=50,
            lot_area=10000, borough=5, community_district=3,
        )
        # Only market-rate (50) units require parking in zone 3
        assert result["residential_spaces_required"] == 25  # 50 * 0.50

    def test_parking_zone_name_in_result(self):
        result = calculate_parking(
            "R7A", unit_count=10, lot_area=5000,
            borough=1, community_district=5,
        )
        assert "parking_zone_name" in result
        assert result["parking_zone_name"] == "Manhattan Core"


class TestUAPScenario:
    """Test UAP scenario generation in the calculator."""

    def test_uap_scenario_generated_for_r7a(self):
        lot = LotProfile(
            bbl="3012340001", borough=3, block=1234, lot=1,
            zoning_districts=["R7A"],
            lot_area=10000, lot_frontage=50, lot_depth=200,
            lot_type="interior", street_width="narrow",
        )
        result = calc.calculate(lot)
        names = [s.name for s in result["scenarios"]]
        assert "UAP (City of Yes)" in names

    def test_uap_scenario_higher_far_than_base(self):
        lot = LotProfile(
            bbl="3012340001", borough=3, block=1234, lot=1,
            zoning_districts=["R7A"],
            lot_area=10000, lot_frontage=50, lot_depth=200,
            lot_type="interior", street_width="narrow",
        )
        result = calc.calculate(lot)
        base = next(s for s in result["scenarios"] if s.name == "Max Residential")
        uap = next(s for s in result["scenarios"] if s.name == "UAP (City of Yes)")
        assert uap.total_gross_sf >= base.total_gross_sf

    def test_uap_not_generated_for_r1(self):
        lot = LotProfile(
            bbl="5012340001", borough=5, block=1234, lot=1,
            zoning_districts=["R1"],
            lot_area=5000, lot_frontage=50, lot_depth=100,
            lot_type="interior", street_width="narrow",
        )
        result = calc.calculate(lot)
        names = [s.name for s in result["scenarios"]]
        assert "UAP (City of Yes)" not in names


class TestCityOfYesSummary:
    """Test the comprehensive City of Yes summary."""

    def test_summary_has_provisions(self):
        summary = get_city_of_yes_summary("R7A", lot_area=10000)
        assert summary["city_of_yes_applicable"] is True
        assert len(summary["provisions"]) >= 2  # At minimum: UAP + parking

    def test_summary_includes_uap(self):
        summary = get_city_of_yes_summary("R7A", lot_area=10000)
        uap = next(
            (p for p in summary["provisions"] if "UAP" in p["name"]), None
        )
        assert uap is not None
        assert uap["applicable"] is True

    def test_summary_includes_parking_zone(self):
        summary = get_city_of_yes_summary(
            "R7A", lot_area=10000, borough=1, community_district=5,
        )
        parking = next(
            (p for p in summary["provisions"] if "Parking" in p["name"]), None
        )
        assert parking is not None
        assert parking["parking_zone"] == 0

    def test_city_of_yes_in_calculator_result(self):
        lot = LotProfile(
            bbl="3012340001", borough=3, block=1234, lot=1,
            zoning_districts=["R7A"],
            lot_area=10000, lot_frontage=50, lot_depth=200,
            lot_type="interior", street_width="narrow",
        )
        result = calc.calculate(lot)
        assert "city_of_yes" in result
        assert result["city_of_yes"]["city_of_yes_applicable"] is True


class TestADU:
    """Test ADU provisions."""

    def test_r3a_adu_eligible(self):
        assert is_adu_eligible("R3A") is True

    def test_r7a_not_adu_eligible(self):
        assert is_adu_eligible("R7A") is False

    def test_adu_rules(self):
        rules = get_adu_rules("R3A")
        assert rules is not None
        assert rules["max_size_sf"] == 800
        assert rules["max_units_per_lot"] == 1


class TestOfficeConversion:
    """Test office-to-residential conversion eligibility."""

    def test_c6_eligible(self):
        assert is_office_conversion_eligible("C6-2") is True

    def test_m1_5_eligible(self):
        assert is_office_conversion_eligible("M1-5") is True

    def test_r7a_not_eligible(self):
        assert is_office_conversion_eligible("R7A") is False

    def test_too_new_building(self):
        assert is_office_conversion_eligible("C6-2", building_year=2000) is False

    def test_old_building(self):
        assert is_office_conversion_eligible("C6-2", building_year=1985) is True


class TestCalculateUAPScenario:
    """Test the calculate_uap_scenario function."""

    def test_r7a_uap_scenario(self):
        result = calculate_uap_scenario("R7A", lot_area=10000, street_width="wide")
        assert result is not None
        assert result["base_far"] == 4.0
        assert result["uap_far"] == 5.01
        assert result["bonus_far"] == pytest.approx(1.01, abs=0.01)
        assert result["base_zfa"] == 40000
        assert result["uap_zfa"] == 50100
        assert result["max_height_with_uap"] == 115

    def test_r1_no_uap(self):
        result = calculate_uap_scenario("R1", lot_area=5000)
        assert result is None

    def test_r6a_uap_scenario(self):
        result = calculate_uap_scenario("R6A", lot_area=10000)
        assert result is not None
        assert result["base_far"] == 3.0
        assert result["uap_far"] == 3.9
        assert result["affordable_far"] == pytest.approx(0.9, abs=0.01)
