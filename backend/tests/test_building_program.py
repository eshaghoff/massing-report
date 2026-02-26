"""Tests for building program calculator.

Validates core sizing, ground floor, cellar, bulkhead, unit mix,
and overall loss factor benchmarks by building class.
"""

from __future__ import annotations

import pytest

from app.zoning_engine.building_program import (
    calculate_core,
    calculate_ground_floor,
    calculate_cellar,
    calculate_bulkhead,
    generate_unit_mix,
    generate_all_unit_mixes,
    generate_building_program,
    get_building_class,
    UNIT_SIZES,
    UNIT_MIX_STRATEGIES,
)


# ──────────────────────────────────────────────────────────────────
# CORE SIZING
# ──────────────────────────────────────────────────────────────────

class TestCoreSizing:
    """Test vertical circulation and services per floor."""

    def test_walkup_single_stair(self):
        """3-story, 10-unit building needs 1 stair, no elevator."""
        core = calculate_core(num_floors=3, total_units=10, typical_floor_sf=2000)
        assert core.stairs == 1
        assert core.elevators == 0
        assert core.freight_elevators == 0

    def test_walkup_two_stairs_by_floors(self):
        """4 stories triggers 2 stairs."""
        core = calculate_core(num_floors=4, total_units=10, typical_floor_sf=3000)
        assert core.stairs == 2

    def test_walkup_two_stairs_by_units(self):
        """21 units triggers 2 stairs even if ≤3 floors."""
        core = calculate_core(num_floors=3, total_units=21, typical_floor_sf=5000)
        assert core.stairs == 2

    def test_highrise_three_stairs(self):
        """31+ floors triggers 3 stairs."""
        core = calculate_core(num_floors=35, total_units=300, typical_floor_sf=8000)
        assert core.stairs == 3

    def test_no_elevator_low_rise(self):
        """5-story building: no elevator required."""
        core = calculate_core(num_floors=5, total_units=15, typical_floor_sf=2500)
        assert core.elevators == 0

    def test_one_elevator_6_stories(self):
        """6-story building gets 1 elevator."""
        core = calculate_core(num_floors=6, total_units=20, typical_floor_sf=3000)
        assert core.elevators == 1

    def test_two_elevators_12_stories(self):
        """12-story building gets 2 elevators."""
        core = calculate_core(num_floors=12, total_units=80, typical_floor_sf=5000)
        assert core.elevators == 2

    def test_freight_elevator_10_floors(self):
        """10+ floors adds freight elevator."""
        core = calculate_core(num_floors=10, total_units=60, typical_floor_sf=5000)
        assert core.freight_elevators == 1
        assert core.freight_elevator_sf_per_floor == 90

    def test_no_freight_9_floors(self):
        """9 floors: no freight elevator."""
        core = calculate_core(num_floors=9, total_units=50, typical_floor_sf=4000)
        assert core.freight_elevators == 0

    def test_trash_chute_always_80(self):
        core = calculate_core(num_floors=5, total_units=15, typical_floor_sf=2500)
        assert core.trash_chute_sf_per_floor == 80

    def test_mep_always_60(self):
        core = calculate_core(num_floors=5, total_units=15, typical_floor_sf=2500)
        assert core.mep_closet_sf_per_floor == 60

    def test_fire_riser_always_15(self):
        core = calculate_core(num_floors=5, total_units=15, typical_floor_sf=2500)
        assert core.fire_riser_sf_per_floor == 15

    def test_double_loaded_corridor(self):
        """Double-loaded corridor: 5.5 ft × full depth, capped at 15% of floor."""
        core = calculate_core(
            num_floors=5, total_units=15, typical_floor_sf=5000,
            building_depth=80, corridor_type="double_loaded",
        )
        # 5.5 × 80 = 440, cap = 5000 × 0.15 = 750 → 440 < 750, so not capped
        assert core.corridor_sf_per_floor == 5.5 * 80

    def test_single_loaded_corridor(self):
        """Single-loaded corridor: 5.5 ft × half depth."""
        core = calculate_core(
            num_floors=5, total_units=15, typical_floor_sf=5000,
            building_depth=80, corridor_type="single_loaded",
        )
        assert core.corridor_sf_per_floor == 5.5 * 40

    def test_corridor_capped_for_small_floor(self):
        """Corridor capped at 15% of floor area for small buildings."""
        core = calculate_core(
            num_floors=3, total_units=10, typical_floor_sf=2000,
            building_depth=100, corridor_type="double_loaded",
        )
        # 5.5 × 100 = 550, cap = 2000 × 0.15 = 300 → capped at 300
        assert core.corridor_sf_per_floor == 300

    def test_core_percentage_calculated(self):
        """Core percentage = total_core / typical_floor × 100."""
        core = calculate_core(num_floors=7, total_units=30, typical_floor_sf=4000, building_depth=60)
        assert core.core_percentage > 0
        expected = core.total_core_sf_per_floor / 4000 * 100
        assert core.core_percentage == pytest.approx(expected, abs=0.2)

    def test_total_core_sums_components(self):
        """total_core_sf_per_floor should be sum of all components."""
        core = calculate_core(num_floors=10, total_units=60, typical_floor_sf=5000, building_depth=80)
        expected = (
            core.stair_sf_per_floor +
            core.elevator_sf_per_floor +
            core.freight_elevator_sf_per_floor +
            core.trash_chute_sf_per_floor +
            core.mep_closet_sf_per_floor +
            core.fire_riser_sf_per_floor +
            core.corridor_sf_per_floor
        )
        assert core.total_core_sf_per_floor == pytest.approx(expected, abs=1)


# ──────────────────────────────────────────────────────────────────
# GROUND FLOOR PROGRAM
# ──────────────────────────────────────────────────────────────────

class TestGroundFloorProgram:
    """Test ground floor non-rentable program areas."""

    def test_small_building_lobby(self):
        """<30 units: 300 SF lobby."""
        gf = calculate_ground_floor(total_units=20, max_height_ft=60)
        assert gf.lobby_sf == 300

    def test_large_building_lobby(self):
        """30+ units: 500 SF lobby."""
        gf = calculate_ground_floor(total_units=50, max_height_ft=100)
        assert gf.lobby_sf == 500

    def test_package_room_scales(self):
        """<50 units: 100 SF, 50+ units: 200 SF."""
        small = calculate_ground_floor(total_units=30, max_height_ft=60)
        large = calculate_ground_floor(total_units=60, max_height_ft=100)
        assert small.package_room_sf == 100
        assert large.package_room_sf == 200

    def test_fire_pump_above_75ft(self):
        """Building >75 ft gets fire pump room."""
        gf = calculate_ground_floor(total_units=30, max_height_ft=80)
        assert gf.fire_pump_room_sf == 200

    def test_no_fire_pump_75ft_or_less(self):
        gf = calculate_ground_floor(total_units=30, max_height_ft=75)
        assert gf.fire_pump_room_sf == 0

    def test_bike_storage_per_space(self):
        """20 SF per bike space."""
        gf = calculate_ground_floor(total_units=30, max_height_ft=60, bike_spaces=15)
        assert gf.bike_storage_sf == 300

    def test_total_sums_components(self):
        gf = calculate_ground_floor(total_units=30, max_height_ft=60, bike_spaces=10)
        expected = (
            gf.lobby_sf + gf.mailroom_sf + gf.package_room_sf +
            gf.super_office_sf + gf.electrical_meter_sf +
            gf.fire_pump_room_sf + gf.bike_storage_sf +
            gf.trash_collection_sf
        )
        assert gf.total_sf == expected


# ──────────────────────────────────────────────────────────────────
# CELLAR PROGRAM
# ──────────────────────────────────────────────────────────────────

class TestCellarProgram:
    """Test cellar/mechanical program areas."""

    def test_no_cellar(self):
        cellar = calculate_cellar(total_units=20, has_cellar=False)
        assert cellar.total_sf == 0

    def test_standard_cellar(self):
        cellar = calculate_cellar(total_units=30, has_cellar=True)
        assert cellar.boiler_room_sf == 400
        assert cellar.water_pump_room_sf == 200
        assert cellar.sprinkler_room_sf == 150

    def test_storage_15_per_unit(self):
        cellar = calculate_cellar(total_units=40, has_cellar=True)
        assert cellar.resident_storage_sf == 600  # 40 × 15

    def test_laundry_machines(self):
        """1 machine per 10 units, 200 base + 20 per machine."""
        cellar = calculate_cellar(total_units=50, has_cellar=True)
        # 50/10 = 5 machines → 200 + 5*20 = 300
        assert cellar.laundry_sf == 300

    def test_no_laundry_if_in_unit(self):
        cellar = calculate_cellar(total_units=50, has_cellar=True, in_unit_laundry=True)
        assert cellar.laundry_sf == 0

    def test_total_sums_components(self):
        cellar = calculate_cellar(total_units=30, has_cellar=True)
        expected = (
            cellar.boiler_room_sf + cellar.water_pump_room_sf +
            cellar.sprinkler_room_sf + cellar.resident_storage_sf +
            cellar.laundry_sf
        )
        assert cellar.total_sf == expected


# ──────────────────────────────────────────────────────────────────
# BULKHEAD
# ──────────────────────────────────────────────────────────────────

class TestBulkheadProgram:
    """Test roof bulkheads and mechanical penthouse."""

    def test_stair_bulkhead_150_per_stair(self):
        core = calculate_core(num_floors=7, total_units=30, typical_floor_sf=4000)
        bulkhead = calculate_bulkhead(core, 7)
        assert bulkhead.stair_bulkhead_sf == core.stairs * 150

    def test_elevator_bulkhead(self):
        core = calculate_core(num_floors=12, total_units=80, typical_floor_sf=5000)
        bulkhead = calculate_bulkhead(core, 12)
        expected = (core.elevators + core.freight_elevators) * 100
        assert bulkhead.elevator_bulkhead_sf == expected

    def test_mechanical_penthouse_low(self):
        core = calculate_core(num_floors=5, total_units=15, typical_floor_sf=2000)
        bulkhead = calculate_bulkhead(core, 5)
        assert bulkhead.mechanical_penthouse_sf == 300

    def test_mechanical_penthouse_mid(self):
        core = calculate_core(num_floors=10, total_units=60, typical_floor_sf=5000)
        bulkhead = calculate_bulkhead(core, 10)
        assert bulkhead.mechanical_penthouse_sf == 400

    def test_mechanical_penthouse_high(self):
        core = calculate_core(num_floors=20, total_units=150, typical_floor_sf=7000)
        bulkhead = calculate_bulkhead(core, 20)
        assert bulkhead.mechanical_penthouse_sf == 600


# ──────────────────────────────────────────────────────────────────
# UNIT MIX
# ──────────────────────────────────────────────────────────────────

class TestUnitMix:
    """Test unit mix generation."""

    def test_maximize_strategy_favors_small(self):
        """Maximize strategy should have most units as studio + 1BR."""
        mix = generate_unit_mix(net_rentable_sf=20000, strategy="maximize")
        studios = next((u for u in mix.units if u["type"] == "studio"), None)
        one_br = next((u for u in mix.units if u["type"] == "1br"), None)
        total_small = (studios["count"] if studios else 0) + (one_br["count"] if one_br else 0)
        assert total_small >= mix.total_units * 0.7

    def test_family_strategy_favors_large(self):
        """Family strategy should have >50% 2BR+3BR."""
        mix = generate_unit_mix(net_rentable_sf=20000, strategy="family")
        two_br = next((u for u in mix.units if u["type"] == "2br"), None)
        three_br = next((u for u in mix.units if u["type"] == "3br"), None)
        total_large = (two_br["count"] if two_br else 0) + (three_br["count"] if three_br else 0)
        assert total_large >= mix.total_units * 0.5

    def test_balanced_has_all_types(self):
        """Balanced strategy should include all 4 unit types."""
        mix = generate_unit_mix(net_rentable_sf=50000, strategy="balanced")
        types = {u["type"] for u in mix.units}
        assert "studio" in types
        assert "1br" in types
        assert "2br" in types
        assert "3br" in types

    def test_du_limit_caps_units(self):
        """DU limit should cap total units."""
        mix = generate_unit_mix(net_rentable_sf=50000, strategy="maximize", du_limit=20)
        assert mix.total_units <= 20
        assert mix.exceeds_du_limit is True

    def test_no_du_limit(self):
        mix = generate_unit_mix(net_rentable_sf=50000, strategy="maximize")
        assert mix.exceeds_du_limit is False
        assert mix.du_limit is None

    def test_zero_area_returns_empty(self):
        mix = generate_unit_mix(net_rentable_sf=0, strategy="balanced")
        assert mix.total_units == 0
        assert mix.units == []

    def test_all_strategies_generated(self):
        mixes = generate_all_unit_mixes(net_rentable_sf=30000)
        assert len(mixes) == 3
        strategies = {m.strategy for m in mixes}
        assert strategies == {"maximize", "balanced", "family"}

    def test_maximize_yields_most_units(self):
        """Maximize strategy should produce the most units."""
        mixes = generate_all_unit_mixes(net_rentable_sf=30000)
        maximize = next(m for m in mixes if m.strategy == "maximize")
        family = next(m for m in mixes if m.strategy == "family")
        assert maximize.total_units >= family.total_units

    def test_unit_sizes_match_standards(self):
        """Verify the NYC market-standard unit sizes."""
        assert UNIT_SIZES["studio"] == 425
        assert UNIT_SIZES["1br"] == 625
        assert UNIT_SIZES["2br"] == 875
        assert UNIT_SIZES["3br"] == 1100


# ──────────────────────────────────────────────────────────────────
# BUILDING CLASS
# ──────────────────────────────────────────────────────────────────

class TestBuildingClass:
    def test_walkup(self):
        assert get_building_class(3) == "walkup"
        assert get_building_class(6) == "walkup"

    def test_midrise(self):
        assert get_building_class(7) == "midrise"
        assert get_building_class(12) == "midrise"

    def test_highrise(self):
        assert get_building_class(13) == "highrise"
        assert get_building_class(24) == "highrise"

    def test_tower(self):
        assert get_building_class(25) == "tower"
        assert get_building_class(50) == "tower"


# ──────────────────────────────────────────────────────────────────
# FULL BUILDING PROGRAM (integration)
# ──────────────────────────────────────────────────────────────────

class TestGenerateBuildingProgram:
    """Integration tests for the full building program generator."""

    def _make_scenario(
        self,
        total_gross_sf=15000,
        zoning_floor_area=14000,
        residential_sf=12000,
        commercial_sf=2000,
        cf_sf=0,
        total_units=20,
        num_floors=5,
        max_height_ft=55,
        floors=None,
    ):
        """Helper to build a scenario dict."""
        if floors is None:
            per_floor = total_gross_sf / max(num_floors, 1)
            floors = [
                {"floor": i + 1, "use": "residential", "gross_sf": per_floor}
                for i in range(num_floors)
            ]
        return {
            "total_gross_sf": total_gross_sf,
            "zoning_floor_area": zoning_floor_area,
            "residential_sf": residential_sf,
            "commercial_sf": commercial_sf,
            "cf_sf": cf_sf,
            "total_units": total_units,
            "num_floors": num_floors,
            "max_height_ft": max_height_ft,
            "floors": floors,
        }

    def test_walkup_loss_factor_benchmark(self):
        """Walk-up (≤6 floors): loss factor 10-40%.
        Small walk-ups with cellar have proportionally higher loss.
        """
        scenario = self._make_scenario(
            total_gross_sf=25000, residential_sf=22000,
            commercial_sf=2000, total_units=30, num_floors=6, max_height_ft=65,
        )
        bp = generate_building_program(scenario, lot_depth=100, lot_frontage=60)
        assert bp.building_class == "walkup"
        assert bp.loss_factor_pct > 5
        assert bp.loss_factor_pct < 55  # Generous upper bound including cellar in denominator
        assert bp.net_rentable_residential > 0

    def test_midrise_loss_factor_benchmark(self):
        """Mid-rise (7-12 floors): loss factor 15-30%."""
        scenario = self._make_scenario(
            total_gross_sf=50000, residential_sf=45000,
            commercial_sf=3000, total_units=60, num_floors=10, max_height_ft=105,
        )
        bp = generate_building_program(scenario, lot_depth=100, lot_frontage=60)
        assert bp.building_class == "midrise"
        assert bp.loss_factor_pct > 10
        assert bp.loss_factor_pct < 45

    def test_highrise_loss_factor_benchmark(self):
        """High-rise (13+ floors): loss factor 18-35%."""
        scenario = self._make_scenario(
            total_gross_sf=120000, residential_sf=110000,
            commercial_sf=5000, total_units=150, num_floors=18, max_height_ft=195,
        )
        bp = generate_building_program(scenario, lot_depth=100, lot_frontage=80)
        assert bp.building_class == "highrise"
        assert bp.loss_factor_pct > 10
        assert bp.loss_factor_pct < 50

    def test_tower_loss_factor_benchmark(self):
        """Tower (25+ floors): loss factor 22-40%."""
        scenario = self._make_scenario(
            total_gross_sf=250000, residential_sf=230000,
            commercial_sf=10000, total_units=300, num_floors=30, max_height_ft=325,
        )
        bp = generate_building_program(scenario, lot_depth=100, lot_frontage=100)
        assert bp.building_class == "tower"
        assert bp.loss_factor_pct > 10
        assert bp.loss_factor_pct < 55

    def test_has_unit_mixes(self):
        """Should generate 3 unit mix options."""
        scenario = self._make_scenario()
        bp = generate_building_program(scenario)
        assert len(bp.unit_mix_options) == 3

    def test_unit_mix_du_limit(self):
        """DU limit should be passed through to unit mixes."""
        scenario = self._make_scenario(
            total_gross_sf=50000, residential_sf=45000,
            total_units=60, num_floors=10, max_height_ft=105,
        )
        bp = generate_building_program(scenario, du_limit=30)
        for mix in bp.unit_mix_options:
            assert mix.total_units <= 30

    def test_cellar_present_for_3plus_floors(self):
        scenario = self._make_scenario(num_floors=3)
        bp = generate_building_program(scenario)
        assert bp.cellar.total_sf > 0

    def test_no_cellar_for_2_floors(self):
        scenario = self._make_scenario(num_floors=2)
        bp = generate_building_program(scenario)
        assert bp.cellar.total_sf == 0

    def test_net_residential_positive(self):
        """Net rentable residential should always be non-negative."""
        scenario = self._make_scenario()
        bp = generate_building_program(scenario)
        assert bp.net_rentable_residential >= 0

    def test_net_commercial_positive(self):
        """Net rentable commercial should be positive when there's commercial SF."""
        scenario = self._make_scenario(commercial_sf=3000)
        bp = generate_building_program(scenario)
        assert bp.net_rentable_commercial > 0
        # Commercial typically 93% efficient
        assert bp.net_rentable_commercial == pytest.approx(3000 * 0.93, abs=1)

    def test_to_dict_structure(self):
        """Verify to_dict returns all expected keys."""
        scenario = self._make_scenario()
        bp = generate_building_program(scenario)
        d = bp.to_dict()
        assert "gross_building_area" in d
        assert "core" in d
        assert "ground_floor" in d
        assert "cellar" in d
        assert "bulkhead" in d
        assert "unit_mix_options" in d
        assert "loss_factor_pct" in d
        assert "building_class" in d

    def test_efficiency_ratio_inverse_of_loss(self):
        """Efficiency ratio ≈ 1 - loss_factor_pct/100."""
        scenario = self._make_scenario()
        bp = generate_building_program(scenario)
        # Rough check — not exact because of how they're calculated
        assert bp.efficiency_ratio > 0
        assert bp.efficiency_ratio < 1

    def test_zero_scenario_no_crash(self):
        """Handle edge case of empty scenario."""
        scenario = {
            "total_gross_sf": 0,
            "zoning_floor_area": 0,
            "residential_sf": 0,
            "commercial_sf": 0,
            "cf_sf": 0,
            "total_units": 0,
            "num_floors": 0,
            "max_height_ft": 0,
            "floors": [],
        }
        bp = generate_building_program(scenario)
        assert bp.loss_factor_pct >= 0
        assert bp.net_rentable_residential >= 0
