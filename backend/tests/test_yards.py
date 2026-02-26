"""Tests for yard requirements calculator."""

from __future__ import annotations

import pytest

from app.zoning_engine.yards import get_yard_requirements


class TestRearYard:
    """Test rear yard requirements."""

    def test_low_density_30ft(self):
        result = get_yard_requirements("R3-1", lot_depth=100)
        assert result["rear_yard"] == 30

    def test_high_density_20pct(self):
        result = get_yard_requirements("R8A", lot_depth=100)
        assert result["rear_yard"] <= 30
        assert result["rear_yard"] >= 20

    def test_through_lot_no_rear_yard(self):
        # Through lots > 110 ft deep require rear yard equivalent (40 ft center strip)
        result = get_yard_requirements("R7A", lot_type="through", lot_depth=150)
        assert result["rear_yard"] == 0
        assert result["rear_yard_equivalent"] == 40

    def test_short_through_lot_no_equivalent(self):
        # Through lots ≤ 110 ft: treat as two separate buildings, no rear yard equiv
        result = get_yard_requirements("R7A", lot_type="through", lot_depth=100)
        assert result["rear_yard"] == 0
        assert result["rear_yard_equivalent"] == 0

    def test_deep_through_lot_60ft_equivalent(self):
        # Through lots > 180 ft deep: 60 ft center open area
        result = get_yard_requirements("R7A", lot_type="through", lot_depth=200)
        assert result["rear_yard"] == 0
        assert result["rear_yard_equivalent"] == 60

    def test_manufacturing_no_rear(self):
        result = get_yard_requirements("M1-1", lot_depth=100)
        assert result["rear_yard"] == 0


class TestSideYards:
    """Test side yard requirements."""

    def test_r1_requires_side_yards(self):
        result = get_yard_requirements("R1", lot_depth=100)
        assert result["side_yards_required"] is True
        assert result["side_yard_each"] > 0

    def test_r7a_no_side_yards(self):
        result = get_yard_requirements("R7A", lot_depth=100)
        assert result["side_yards_required"] is False

    def test_r5_attached_no_side_yards(self):
        """R5 is an attached building type — no side yards (party walls)."""
        result = get_yard_requirements("R5", lot_depth=100)
        assert result["side_yards_required"] is False
        assert result["side_yard_each"] == 0


class TestFrontYard:
    """Test front yard requirements."""

    def test_r1_has_front_yard(self):
        result = get_yard_requirements("R1", lot_depth=100)
        assert result["front_yard"] > 0

    def test_r7a_no_front_yard(self):
        result = get_yard_requirements("R7A", lot_depth=100)
        assert result["front_yard"] == 0


class TestLotCoverage:
    """Test lot coverage limits."""

    def test_r7a_interior_65pct(self):
        result = get_yard_requirements("R7A", lot_type="interior")
        assert result["lot_coverage_max"] == 65

    def test_r7a_corner_80pct(self):
        result = get_yard_requirements("R7A", lot_type="corner")
        assert result["lot_coverage_max"] == 80

    def test_r8a_interior_70pct(self):
        result = get_yard_requirements("R8A", lot_type="interior")
        assert result["lot_coverage_max"] == 70

    def test_r1_low_coverage(self):
        result = get_yard_requirements("R1", lot_type="interior")
        assert result["lot_coverage_max"] is not None
        assert result["lot_coverage_max"] <= 40
