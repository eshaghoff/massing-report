"""Tests for dormer rules in contextual districts."""

from __future__ import annotations

import pytest

from app.zoning_engine.dormers import (
    get_dormer_rules,
    calculate_upper_floor_area,
    DORMER_ELIGIBLE_DISTRICTS,
)


class TestDormerEligibility:
    """Test which districts are eligible for dormers."""

    def test_r7a_eligible(self):
        rules = get_dormer_rules("R7A")
        assert rules["eligible"] is True

    def test_r8a_eligible(self):
        rules = get_dormer_rules("R8A")
        assert rules["eligible"] is True

    def test_r6_not_eligible(self):
        # R6 (non-contextual) is NOT eligible for dormers
        rules = get_dormer_rules("R6")
        assert rules["eligible"] is False

    def test_r1_not_eligible(self):
        rules = get_dormer_rules("R1")
        assert rules["eligible"] is False

    def test_dormer_width_60pct(self):
        rules = get_dormer_rules("R7A")
        assert rules["max_width_pct"] == 0.60


class TestDormerFloorArea:
    """Test upper floor area calculations with dormers."""

    def test_dormer_adds_area_vs_full_setback(self):
        # With dormer: upper floor retains more area than full setback
        lot_frontage = 50
        lot_depth = 100
        setback = 15
        base_fp = lot_frontage * lot_depth  # 5000 SF

        # Full setback (no dormer): 50 * (100-15) = 4250 SF
        full_setback_area = lot_frontage * (lot_depth - setback)

        # With dormer: 60% at full depth + 40% with setback
        dormer_area = calculate_upper_floor_area(
            base_fp, lot_frontage, lot_depth, setback, "R7A"
        )

        assert dormer_area > full_setback_area

    def test_no_setback_returns_full_footprint(self):
        area = calculate_upper_floor_area(5000, 50, 100, 0, "R7A")
        assert area == 5000  # No setback = full footprint

    def test_non_contextual_no_dormer(self):
        # R6 non-contextual: just full setback reduction
        area = calculate_upper_floor_area(5000, 50, 100, 10, "R6")
        # Should be 50 * (100-10) = 4500 (simple setback)
        assert area == 4500

    def test_all_contextual_eligible(self):
        for dist in DORMER_ELIGIBLE_DISTRICTS:
            rules = get_dormer_rules(dist)
            assert rules["eligible"] is True, f"{dist} should be dormer-eligible"
