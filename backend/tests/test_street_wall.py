"""Tests for street wall rules and sliver law."""

from __future__ import annotations

import pytest

from app.zoning_engine.street_wall import (
    get_sliver_law_height,
    get_street_wall_rules,
    SLIVER_LAW_THRESHOLD,
)


class TestSliverLaw:
    """Test sliver law height restrictions."""

    def test_narrow_lot_r6(self):
        # R6, 30 ft lot: height limited to 30 * 2.7 = 81 ft
        height = get_sliver_law_height("R6", 30)
        assert height is not None
        assert abs(height - 81.0) < 0.1

    def test_narrow_lot_r8(self):
        # R8, 40 ft lot: 40 * 3.4 = 136 ft
        height = get_sliver_law_height("R8", 40)
        assert height is not None
        assert abs(height - 136.0) < 0.1

    def test_wide_lot_not_affected(self):
        # Lots >= 45 ft are not affected
        height = get_sliver_law_height("R8", 50)
        assert height is None

    def test_exactly_45ft_not_affected(self):
        height = get_sliver_law_height("R8", 45)
        assert height is None

    def test_r10_sliver(self):
        # R10, 35 ft lot: 35 * 5.6 = 196 ft
        height = get_sliver_law_height("R10", 35)
        assert height is not None
        assert abs(height - 196.0) < 0.1

    def test_qh_district_not_affected(self):
        # R7A is QH, not subject to sliver law
        height = get_sliver_law_height("R7A", 30)
        assert height is None

    def test_c6_commercial_sliver(self):
        # C6-2 maps to R8 equivalent
        height = get_sliver_law_height("C6-2", 30)
        assert height is not None


class TestStreetWallRules:
    """Test Quality Housing street wall requirements."""

    def test_r7a_has_street_wall(self):
        rules = get_street_wall_rules("R7A", "narrow")
        assert rules["applies"] is True
        assert rules["min_base_pct"] >= 50

    def test_r8a_wide_street(self):
        rules = get_street_wall_rules("R8A", "wide")
        assert rules["applies"] is True
        assert rules["min_base_pct"] >= 70

    def test_r1_no_street_wall(self):
        # Low-density districts don't have QH street wall rules
        rules = get_street_wall_rules("R1", "narrow")
        assert rules["applies"] is False

    def test_r10a_has_street_wall(self):
        rules = get_street_wall_rules("R10A", "narrow")
        assert rules["applies"] is True

    def test_non_contextual_no_street_wall(self):
        # R6 (non-contextual) doesn't have mandatory QH street wall
        rules = get_street_wall_rules("R6", "narrow")
        assert rules["applies"] is False
