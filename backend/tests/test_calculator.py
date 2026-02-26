"""Tests for the main ZoningCalculator."""

from __future__ import annotations

import pytest

from app.zoning_engine.calculator import ZoningCalculator
from app.models.schemas import LotProfile


@pytest.fixture
def calculator():
    return ZoningCalculator()


def _make_lot(
    district: str = "R7A",
    lot_area: float = 5000,
    lot_frontage: float = 50,
    lot_depth: float = 100,
    street_width: str = "narrow",
    lot_type: str = "interior",
    overlays: list = None,
    is_mih: bool = False,
) -> LotProfile:
    return LotProfile(
        bbl="3012340001",
        borough=3,
        block=1234,
        lot=1,
        lot_area=lot_area,
        lot_frontage=lot_frontage,
        lot_depth=lot_depth,
        lot_type=lot_type,
        street_width=street_width,
        zoning_districts=[district],
        overlays=overlays or [],
        special_districts=[],
        split_zone=False,
        is_mih_area=is_mih,
        is_historic_district=False,
        coastal_zone=False,
    )


class TestEnvelopeCalculation:
    """Test zoning envelope computation."""

    def test_r7a_envelope(self, calculator):
        lot = _make_lot("R7A", lot_area=5000)
        env = calculator.calculate_envelope(lot, "R7A")
        assert env.residential_far == 4.0
        assert env.max_residential_zfa == 20000
        assert env.quality_housing is True
        assert env.max_building_height is not None

    def test_r8_qh_envelope_wide(self, calculator):
        """R8 QH on wide street: FAR 7.2 (R8A equivalent)."""
        lot = _make_lot("R8", lot_area=10000, street_width="wide")
        env = calculator.calculate_envelope(lot, "R8")
        assert env.residential_far == 7.2
        assert env.max_residential_zfa == pytest.approx(72000)

    def test_r8_qh_envelope_narrow(self, calculator):
        """R8 QH on narrow street: FAR 6.02."""
        lot = _make_lot("R8", lot_area=10000, street_width="narrow")
        env = calculator.calculate_envelope(lot, "R8")
        assert env.residential_far == 6.02
        assert env.max_residential_zfa == pytest.approx(60200)

    def test_r6a_with_overlay(self, calculator):
        lot = _make_lot("R6A", overlays=["C2-4"])
        env = calculator.calculate_envelope(lot, "R6A")
        assert env.residential_far == 3.0
        assert env.commercial_far == 1.0  # From overlay

    def test_rear_yard_set(self, calculator):
        lot = _make_lot("R7A")
        env = calculator.calculate_envelope(lot, "R7A")
        assert env.rear_yard > 0

    def test_mih_bonus(self, calculator):
        lot = _make_lot("R7A", is_mih=True)
        env = calculator.calculate_envelope(lot, "R7A")
        assert env.ih_bonus_far is not None
        assert env.ih_bonus_far > 0


class TestScenarioGeneration:
    """Test development scenario generation."""

    def test_r7a_generates_scenarios(self, calculator):
        lot = _make_lot("R7A", overlays=["C2-4"])
        result = calculator.calculate(lot)
        assert len(result["scenarios"]) >= 2

    def test_scenario_names_present(self, calculator):
        lot = _make_lot("R7A", overlays=["C2-4"])
        result = calculator.calculate(lot)
        names = [s.name for s in result["scenarios"]]
        assert "Max Residential" in names
        assert "Mixed-Use (Retail + Residential)" in names

    def test_max_residential_far_not_exceeded(self, calculator):
        lot = _make_lot("R7A", lot_area=5000)
        result = calculator.calculate(lot)
        for s in result["scenarios"]:
            if s.name == "Max Residential":
                assert s.far_used <= 4.0 + 0.1  # Slight tolerance

    def test_scenarios_have_floors(self, calculator):
        lot = _make_lot("R7A")
        result = calculator.calculate(lot)
        for s in result["scenarios"]:
            assert s.num_floors > 0
            assert len(s.floors) > 0
            assert s.total_gross_sf > 0

    def test_mixed_use_has_commercial_floor(self, calculator):
        lot = _make_lot("R7A", overlays=["C2-4"])
        result = calculator.calculate(lot)
        mixed = next((s for s in result["scenarios"] if "Mixed-Use" in s.name), None)
        assert mixed is not None
        assert mixed.commercial_sf > 0
        assert mixed.floors[0].use == "commercial"

    def test_unit_mix_generated(self, calculator):
        lot = _make_lot("R7A")
        result = calculator.calculate(lot)
        res = next((s for s in result["scenarios"] if s.name == "Max Residential"), None)
        assert res is not None
        assert res.total_units > 0
        assert res.unit_mix is not None
        assert len(res.unit_mix.units) > 0

    def test_parking_calculated(self, calculator):
        lot = _make_lot("R7A", lot_area=5000)
        result = calculator.calculate(lot)
        res = next((s for s in result["scenarios"] if s.name == "Max Residential"), None)
        assert res is not None
        assert res.parking is not None

    def test_hf_scenario_for_non_contextual(self, calculator):
        """Non-contextual districts should show Height Factor option."""
        lot = _make_lot("R8", lot_area=10000, street_width="wide")
        result = calculator.calculate(lot)
        names = [s.name for s in result["scenarios"]]
        assert "Height Factor Option" in names

    def test_ih_scenario_when_mih(self, calculator):
        lot = _make_lot("R7A", is_mih=True)
        result = calculator.calculate(lot)
        names = [s.name for s in result["scenarios"]]
        assert "With IH Bonus" in names

    def test_cf_scenario_when_cf_far_higher(self, calculator):
        """Should show CF scenario when CF FAR > residential FAR."""
        lot = _make_lot("R6", lot_area=8000)
        result = calculator.calculate(lot)
        # R6 has CF FAR 4.8, residential QH 2.20
        names = [s.name for s in result["scenarios"]]
        assert "Community Facility" in names

    def test_no_residential_in_manufacturing(self, calculator):
        """M2 districts don't allow residential."""
        lot = _make_lot("M2-1", lot_area=10000)
        result = calculator.calculate(lot)
        names = [s.name for s in result["scenarios"]]
        assert "Max Residential" not in names


class TestLossFactorCalculation:
    """Test building efficiency calculations."""

    def test_loss_factor_within_range(self, calculator):
        lot = _make_lot("R7A")
        result = calculator.calculate(lot)
        for s in result["scenarios"]:
            if s.loss_factor:
                assert 0 < s.loss_factor.loss_factor_pct < 40
                assert s.loss_factor.efficiency_ratio > 0.6

    def test_net_less_than_gross(self, calculator):
        lot = _make_lot("R7A")
        result = calculator.calculate(lot)
        for s in result["scenarios"]:
            if s.loss_factor:
                assert s.loss_factor.net_rentable_area < s.loss_factor.gross_building_area


class TestCoreEstimation:
    """Test core size estimation."""

    def test_walkup_no_elevator(self, calculator):
        lot = _make_lot("R5B", lot_area=3000)
        result = calculator.calculate(lot)
        for s in result["scenarios"]:
            if s.core and s.num_floors <= 3:
                assert s.core.elevators == 0

    def test_tall_building_has_elevators(self, calculator):
        lot = _make_lot("R8A", lot_area=10000, street_width="wide")
        result = calculator.calculate(lot)
        for s in result["scenarios"]:
            if s.core and s.num_floors > 6:
                assert s.core.elevators >= 1

    def test_core_has_stairs(self, calculator):
        lot = _make_lot("R7A")
        result = calculator.calculate(lot)
        for s in result["scenarios"]:
            if s.core:
                assert s.core.stairs >= 1


class TestUnitMix:
    """Test unit mix generation."""

    def test_unit_types_present(self, calculator):
        lot = _make_lot("R7A", lot_area=8000)
        result = calculator.calculate(lot)
        res = next((s for s in result["scenarios"] if s.name == "Max Residential"), None)
        if res and res.unit_mix:
            types = [u.type for u in res.unit_mix.units]
            # Should have at least studios and 1BRs
            assert any(t in types for t in ["studio", "1br"])

    def test_unit_sizes_reasonable(self, calculator):
        lot = _make_lot("R7A", lot_area=8000)
        result = calculator.calculate(lot)
        res = next((s for s in result["scenarios"] if s.name == "Max Residential"), None)
        if res and res.unit_mix:
            for u in res.unit_mix.units:
                if u.type == "studio":
                    assert 300 <= u.avg_sf <= 500
                elif u.type == "1br":
                    assert 500 <= u.avg_sf <= 800


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_lot_area(self, calculator):
        lot = _make_lot("R7A", lot_area=0)
        result = calculator.calculate(lot)
        # Should still produce an envelope, even if scenarios are empty
        assert result["zoning_envelope"] is not None

    def test_very_small_lot(self, calculator):
        lot = _make_lot("R7A", lot_area=500, lot_frontage=10, lot_depth=50)
        result = calculator.calculate(lot)
        # Should handle gracefully
        assert result["zoning_envelope"] is not None

    def test_very_large_lot(self, calculator):
        lot = _make_lot("R10A", lot_area=100000, lot_frontage=200, lot_depth=500,
                        street_width="wide")
        result = calculator.calculate(lot)
        assert len(result["scenarios"]) > 0
        for s in result["scenarios"]:
            assert s.num_floors <= 100  # Reasonable cap
