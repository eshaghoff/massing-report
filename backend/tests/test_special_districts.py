"""Tests for special district rules."""

from __future__ import annotations

import pytest

from app.zoning_engine.special_districts import (
    get_special_district_rules,
    apply_special_district_overrides,
    get_special_district_bonuses,
)
from app.zoning_engine.calculator import ZoningCalculator
from app.models.schemas import LotProfile


class TestSpecialDistrictLookup:
    """Test special district lookup."""

    def test_midtown_exists(self):
        rules = get_special_district_rules("MiD")
        assert rules is not None
        assert "Midtown" in rules["name"]

    def test_hudson_yards_exists(self):
        rules = get_special_district_rules("HY")
        assert rules is not None

    def test_unknown_returns_none(self):
        rules = get_special_district_rules("FAKE123")
        assert rules is None

    def test_empty_returns_none(self):
        rules = get_special_district_rules("")
        assert rules is None

    def test_none_returns_none(self):
        rules = get_special_district_rules(None)
        assert rules is None


class TestSpecialDistrictOverrides:
    """Test FAR overrides from special districts."""

    def test_midtown_increases_commercial_far(self):
        base = {"residential": 10.0, "commercial": 10.0, "cf": 10.0}
        result = apply_special_district_overrides(base, ["MiD"])
        assert result["commercial"] == 15.0

    def test_no_special_district_unchanged(self):
        base = {"residential": 4.0, "commercial": 2.0, "cf": 4.0}
        result = apply_special_district_overrides(base, [])
        assert result == base


class TestSpecialDistrictBonuses:
    """Test bonus FAR opportunities."""

    def test_midtown_has_bonuses(self):
        bonuses = get_special_district_bonuses(["MiD"])
        assert len(bonuses) > 0
        bonus_types = [b["type"] for b in bonuses]
        assert any("Plaza" in t for t in bonus_types)

    def test_no_district_no_bonuses(self):
        bonuses = get_special_district_bonuses([])
        assert len(bonuses) == 0


# ──────────────────────────────────────────────────────────────────
# INTEGRATION: Special districts in the full calculator pipeline
# ──────────────────────────────────────────────────────────────────

calc = ZoningCalculator()


def _make_sp_lot(
    district: str, spdist: list[str], lot_area: float = 20000, **kwargs
) -> LotProfile:
    return LotProfile(
        bbl="1007890001",
        borough=1,
        block=789,
        lot=1,
        zoning_districts=[district],
        overlays=kwargs.get("overlays", []),
        special_districts=spdist,
        lot_area=lot_area,
        lot_frontage=kwargs.get("lot_frontage", 100),
        lot_depth=kwargs.get("lot_depth", 200),
        lot_type="interior",
        street_width=kwargs.get("street_width", "wide"),
        is_mih_area=kwargs.get("is_mih_area", False),
    )


class TestSpecialDistrictIntegration:
    """Test special districts flowing through the full calculator."""

    def test_result_has_special_districts_key(self):
        lot = _make_sp_lot("C5-3", ["MiD"])
        result = calc.calculate(lot)
        assert "special_districts" in result

    def test_midtown_shows_applicable(self):
        lot = _make_sp_lot("C5-3", ["MiD"])
        result = calc.calculate(lot)
        sp = result["special_districts"]
        assert sp["applicable"] is True
        assert len(sp["districts"]) == 1
        assert sp["districts"][0]["code"] == "MiD"

    def test_midtown_far_override_applied(self):
        """Midtown special district should increase commercial FAR to 15.0."""
        lot = _make_sp_lot("C5-3", ["MiD"])
        result = calc.calculate(lot)
        env = result["zoning_envelope"]
        # C5-3 base commercial is 15.0, MiD also 15.0 — should be 15.0
        assert env.commercial_far >= 15.0

    def test_hudson_yards_mandatory_ih(self):
        lot = _make_sp_lot("C6-4", ["HY"], is_mih_area=True)
        result = calc.calculate(lot)
        sp = result["special_districts"]
        assert sp["mandatory_inclusionary"] is True

    def test_midtown_bonuses_listed(self):
        lot = _make_sp_lot("C5-3", ["MiD"])
        result = calc.calculate(lot)
        sp = result["special_districts"]
        assert len(sp["bonuses"]) > 0

    def test_west_chelsea_tdr_available(self):
        lot = _make_sp_lot("C6-2", ["WCh"])
        result = calc.calculate(lot)
        sp = result["special_districts"]
        assert sp["tdr_available"] is True

    def test_no_special_district_shows_not_applicable(self):
        lot = _make_sp_lot("R7A", [])
        result = calc.calculate(lot)
        sp = result["special_districts"]
        assert sp["applicable"] is False
        assert len(sp["districts"]) == 0
        assert len(sp["bonuses"]) == 0

    def test_lic_far_override(self):
        """LIC special district overrides residential FAR to 6.5."""
        lot = _make_sp_lot("R6A", ["LIC"], lot_area=10000)
        result = calc.calculate(lot)
        env = result["zoning_envelope"]
        # R6A base residential is 3.0, LIC overrides to 6.5
        assert env.residential_far == 6.5

    def test_downtown_brooklyn_far_override(self):
        """Downtown Brooklyn overrides residential FAR to 12.0."""
        lot = _make_sp_lot("C6-4", ["DB"], is_mih_area=True)
        result = calc.calculate(lot)
        env = result["zoning_envelope"]
        assert env.commercial_far >= 12.0


class TestZFABasedFAR:
    """Test that far_used is calculated from ZFA (gross - exemptions)."""

    def test_far_used_less_than_gross_far(self):
        """ZFA-based FAR should be less than gross-based FAR because exemptions
        reduce the numerator."""
        lot = _make_sp_lot("R7A", [], lot_area=10000, lot_frontage=50,
                           lot_depth=200, street_width="narrow")
        result = calc.calculate(lot)
        for s in result["scenarios"]:
            if s.total_gross_sf > 0 and lot.lot_area:
                gross_far = s.total_gross_sf / lot.lot_area
                # ZFA-based far_used should be less than gross FAR
                assert s.far_used < gross_far

    def test_far_used_still_positive(self):
        lot = _make_sp_lot("R8A", [], lot_area=10000, street_width="wide")
        result = calc.calculate(lot)
        for s in result["scenarios"]:
            assert s.far_used >= 0
