"""
Validation tests against known NYC buildings.

These tests verify that our zoning engine produces results consistent
with actual built/approved projects in NYC.
"""

from __future__ import annotations

import pytest

from app.models.schemas import LotProfile, PlutoData
from app.zoning_engine.calculator import ZoningCalculator
from app.zoning_engine.far_tables import get_far_for_district
from app.zoning_engine.height_setback import get_height_rules
from app.zoning_engine.building_types import get_building_type_for_district


calc = ZoningCalculator()


class TestKnownDistrictRules:
    """Verify FAR and height rules match known values for key districts."""

    def test_r7a_far_is_4(self):
        """R7A is one of the most common contextual districts."""
        far = get_far_for_district("R7A")
        assert far["residential"] == 4.0
        assert far["cf"] == 4.0

    def test_r7d_far_is_4_66(self):
        """R7D FAR corrected to 4.66 per ZR 23-22."""
        far = get_far_for_district("R7D")
        assert far["residential"] == 4.66

    def test_c6_4_is_far_10(self):
        """C6-4 is Downtown Brooklyn's primary commercial district."""
        far = get_far_for_district("C6-4")
        assert far["commercial"] == 10.0
        assert far["residential"] is not None  # Has R10 equivalent

    def test_c5_3_midtown_far_15(self):
        """C5-3 is Midtown's highest-density commercial."""
        far = get_far_for_district("C5-3")
        assert far["commercial"] == 15.0

    def test_r7a_height_narrow_75ft(self):
        """R7A on a narrow street: max 75 ft (ZR 23-432)."""
        height = get_height_rules("R7A", "narrow")
        assert height["max_building_height"] == 75
        assert height["quality_housing"] is True

    def test_r7a_height_wide_85ft(self):
        """R7A on a wide street: max 85 ft (City of Yes, was 80)."""
        height = get_height_rules("R7A", "wide")
        assert height["max_building_height"] == 85


class TestTypicalBrooklynDevelopment:
    """Test a typical Brooklyn R7A development site.

    Many recent Brooklyn developments are in R7A or C4-4A (R7A equivalent)
    zones. A typical site is ~10,000 SF, narrow street, interior lot.
    Expected: ~8 stories, ~40,000 SF, ~55 units.
    """

    @pytest.fixture
    def brooklyn_r7a_lot(self) -> LotProfile:
        return LotProfile(
            bbl="3012340001",
            borough=3,
            block=1234,
            lot=1,
            zoning_districts=["R7A"],
            overlays=["C2-4"],
            lot_area=10000,
            lot_frontage=50,
            lot_depth=200,
            lot_type="interior",
            street_width="narrow",
            is_mih_area=False,
        )

    def test_far_is_4(self, brooklyn_r7a_lot):
        result = calc.calculate(brooklyn_r7a_lot)
        env = result["zoning_envelope"]
        assert env.residential_far == 4.0

    def test_max_zfa(self, brooklyn_r7a_lot):
        result = calc.calculate(brooklyn_r7a_lot)
        env = result["zoning_envelope"]
        assert env.max_residential_zfa == 40000  # 4.0 × 10000

    def test_max_height_75ft(self, brooklyn_r7a_lot):
        """R7A narrow street: 75 ft (ZR 23-432)."""
        result = calc.calculate(brooklyn_r7a_lot)
        env = result["zoning_envelope"]
        assert env.max_building_height == 75

    def test_generates_multiple_scenarios(self, brooklyn_r7a_lot):
        result = calc.calculate(brooklyn_r7a_lot)
        assert len(result["scenarios"]) >= 2

    def test_residential_scenario_units(self, brooklyn_r7a_lot):
        result = calc.calculate(brooklyn_r7a_lot)
        res = next(s for s in result["scenarios"] if s.name == "Max Residential")
        # A 40,000 ZFA building should have 40-70 units
        assert 25 <= res.total_units <= 100

    def test_building_type_is_apartment(self, brooklyn_r7a_lot):
        result = calc.calculate(brooklyn_r7a_lot)
        assert result["building_type"]["building_type"] == "apartment"


class TestManhattanHighDensity:
    """Test a Manhattan high-density site (R10/C6 equivalent).

    Midtown/Downtown sites with FAR 10-15, tower-on-base.
    """

    @pytest.fixture
    def manhattan_c6_4_lot(self) -> LotProfile:
        return LotProfile(
            bbl="1007890001",
            borough=1,
            block=789,
            lot=1,
            zoning_districts=["C6-4"],
            overlays=[],
            lot_area=20000,
            lot_frontage=100,
            lot_depth=200,
            lot_type="interior",
            street_width="wide",
            is_mih_area=True,
            mih_option="option_1",
        )

    def test_high_far(self, manhattan_c6_4_lot):
        result = calc.calculate(manhattan_c6_4_lot)
        env = result["zoning_envelope"]
        assert env.commercial_far == 10.0

    def test_has_residential_via_equivalent(self, manhattan_c6_4_lot):
        result = calc.calculate(manhattan_c6_4_lot)
        env = result["zoning_envelope"]
        # C6-4 → R10 equivalent: residential FAR = 10.0 (or HF/QH dict)
        assert env.residential_far is not None

    def test_generates_tower_scenario(self, manhattan_c6_4_lot):
        result = calc.calculate(manhattan_c6_4_lot)
        tower_scenarios = [s for s in result["scenarios"] if "Tower" in s.name]
        assert len(tower_scenarios) >= 1

    def test_ih_bonus_scenario(self, manhattan_c6_4_lot):
        result = calc.calculate(manhattan_c6_4_lot)
        ih_scenarios = [s for s in result["scenarios"] if "IH" in s.name]
        assert len(ih_scenarios) >= 1

    def test_building_type_tower(self, manhattan_c6_4_lot):
        btype = get_building_type_for_district("C6-4")
        assert btype == "tower_on_base"


class TestLowDensityQueens:
    """Test a low-density Queens residential site (R3A).

    Typical detached/semi-detached district in eastern Queens.
    """

    @pytest.fixture
    def queens_r3a_lot(self) -> LotProfile:
        return LotProfile(
            bbl="4045670001",
            borough=4,
            block=4567,
            lot=1,
            zoning_districts=["R3A"],
            overlays=[],
            lot_area=4750,  # Two 2375 SF lots
            lot_frontage=50,
            lot_depth=95,
            lot_type="interior",
            street_width="narrow",
        )

    def test_far_is_0_5(self, queens_r3a_lot):
        far = get_far_for_district("R3A")
        assert far["residential"] == 0.50

    def test_max_zfa(self, queens_r3a_lot):
        result = calc.calculate(queens_r3a_lot)
        env = result["zoning_envelope"]
        assert env.max_residential_zfa == 2375  # 0.5 × 4750

    def test_height_35ft(self, queens_r3a_lot):
        height = get_height_rules("R3A", "narrow")
        assert height["max_building_height"] == 35  # R3A small-house district = 35 ft

    def test_building_type_semi_detached(self, queens_r3a_lot):
        btype = get_building_type_for_district("R3A")
        assert btype == "semi_detached"

    def test_requires_side_yards(self, queens_r3a_lot):
        result = calc.calculate(queens_r3a_lot)
        env = result["zoning_envelope"]
        assert env.side_yards_required is True


class TestManufacturingDistrict:
    """Test manufacturing district (no residential allowed)."""

    @pytest.fixture
    def m1_4_lot(self) -> LotProfile:
        return LotProfile(
            bbl="4089010001",
            borough=4,
            block=8901,
            lot=1,
            zoning_districts=["M1-4"],
            overlays=[],
            lot_area=15000,
            lot_frontage=75,
            lot_depth=200,
            lot_type="interior",
            street_width="narrow",
        )

    def test_no_residential_far(self, m1_4_lot):
        far = get_far_for_district("M1-4")
        assert far["residential"] is None

    def test_has_commercial_far(self, m1_4_lot):
        far = get_far_for_district("M1-4")
        assert far["commercial"] == 2.0

    def test_has_manufacturing_far(self, m1_4_lot):
        far = get_far_for_district("M1-4")
        assert far["manufacturing"] == 2.0

    def test_no_residential_scenario(self, m1_4_lot):
        result = calc.calculate(m1_4_lot)
        res = [s for s in result["scenarios"] if s.name == "Max Residential"]
        assert len(res) == 0


class TestSliverLotIntegration:
    """Test that sliver law is integrated into envelope calculation."""

    @pytest.fixture
    def narrow_r8_lot(self) -> LotProfile:
        """R8 non-contextual lot that's only 30 ft wide."""
        return LotProfile(
            bbl="1012340001",
            borough=1,
            block=1234,
            lot=1,
            zoning_districts=["R8"],
            overlays=[],
            lot_area=6000,
            lot_frontage=30,   # Narrow! Under 45 ft sliver threshold
            lot_depth=200,
            lot_type="interior",
            street_width="narrow",
        )

    def test_sliver_law_caps_height(self, narrow_r8_lot):
        """R8 HF normally has no height limit, but sliver law caps it."""
        result = calc.calculate(narrow_r8_lot)
        env = result["zoning_envelope"]
        # R8 sliver: 30 * 3.4 = 102 ft
        assert env.max_building_height is not None
        assert env.max_building_height <= 102
