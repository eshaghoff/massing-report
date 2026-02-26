"""Tests for Mandatory Inclusionary Housing options."""

from __future__ import annotations

import pytest

from app.zoning_engine.mih_options import (
    get_mih_bonus_far,
    get_mih_max_far,
    calculate_mih_program,
    get_all_mih_options,
    MIH_OPTIONS,
)


class TestMIHBonusFAR:
    """Test MIH bonus FAR calculations."""

    def test_r7a_bonus(self):
        bonus = get_mih_bonus_far("R7A")
        assert bonus is not None
        assert abs(bonus - 0.6) < 0.01  # 4.6 - 4.0

    def test_r10_bonus(self):
        bonus = get_mih_bonus_far("R10")
        assert bonus is not None
        assert bonus == 2.0  # 12.0 - 10.0

    def test_r1_no_bonus(self):
        bonus = get_mih_bonus_far("R1")
        assert bonus is None

    def test_c6_2_via_equivalent(self):
        # C6-2 → R8 equivalent
        bonus = get_mih_bonus_far("C6-2")
        assert bonus is not None


class TestMIHMaxFAR:
    """Test MIH maximum FAR."""

    def test_r7a_max_far(self):
        max_far = get_mih_max_far("R7A")
        assert max_far == 4.6

    def test_r10_max_far(self):
        max_far = get_mih_max_far("R10")
        assert max_far == 12.0


class TestMIHProgram:
    """Test MIH program calculations."""

    def test_option_1_25_pct_affordable(self):
        program = calculate_mih_program("option_1", 100000)
        assert program["affordable_pct"] == 0.25
        assert program["affordable_sf"] == 25000
        assert program["market_rate_sf"] == 75000

    def test_option_2_30_pct_affordable(self):
        program = calculate_mih_program("option_2", 100000)
        assert program["affordable_pct"] == 0.30
        assert program["affordable_sf"] == 30000

    def test_deep_affordability_20_pct(self):
        program = calculate_mih_program("deep_affordability", 100000)
        assert program["affordable_pct"] == 0.20
        assert program["avg_ami"] == 40

    def test_workforce_115_ami(self):
        program = calculate_mih_program("workforce", 100000)
        assert program["avg_ami"] == 115

    def test_has_rent_schedule(self):
        program = calculate_mih_program("option_1", 100000)
        assert "rent_schedule" in program
        rents = program["rent_schedule"]
        assert len(rents) > 0

    def test_estimated_units_positive(self):
        program = calculate_mih_program("option_1", 100000)
        assert program["estimated_affordable_units"] > 0

    def test_revenue_impact(self):
        program = calculate_mih_program("option_1", 100000)
        assert program["estimated_annual_revenue_impact"] > 0


class TestGetAllMIHOptions:
    """Test comparison of all MIH options."""

    def test_returns_four_options(self):
        options = get_all_mih_options(100000)
        assert len(options) == 4

    def test_options_have_different_amis(self):
        options = get_all_mih_options(100000)
        amis = [o["avg_ami"] for o in options]
        assert len(set(amis)) == 4  # All different

    def test_deep_affordability_lowest_ami(self):
        options = get_all_mih_options(100000)
        amis = {o["option_key"]: o["avg_ami"] for o in options}
        assert amis["deep_affordability"] < amis["option_1"]
        assert amis["option_1"] < amis["option_2"]
