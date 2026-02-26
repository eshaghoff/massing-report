"""Tests for Height Factor open space ratio calculations."""

from __future__ import annotations

import pytest

from app.zoning_engine.open_space_ratio import (
    calculate_hf_far,
    get_required_open_space,
    get_max_floor_area_for_open_space,
    HF_OPEN_SPACE,
)


class TestHFOpenSpace:
    """Test Height Factor open space ratio calculations."""

    def test_r6_hf_max_far(self):
        result = calculate_hf_far("R6", 10000)
        assert result["max_far"] == 2.43
        assert result["is_height_factor"] is True

    def test_r6_hf_min_osr(self):
        result = calculate_hf_far("R6", 10000)
        assert result["min_osr"] == 27.5

    def test_r8_hf(self):
        result = calculate_hf_far("R8", 10000)
        assert result["max_far"] == 6.02
        assert result["min_osr"] == 5.9

    def test_r9_hf(self):
        result = calculate_hf_far("R9", 10000)
        assert result["max_far"] == 7.52

    def test_r10_no_osr(self):
        result = calculate_hf_far("R10", 10000)
        assert result["max_far"] == 10.0
        assert result["min_osr"] == 0  # R10 has no OSR requirement

    def test_non_hf_district(self):
        result = calculate_hf_far("R7A", 10000)
        assert result["is_height_factor"] is False

    def test_min_open_space_positive(self):
        result = calculate_hf_far("R6", 10000)
        assert result["min_open_space_sf"] > 0

    def test_r7_1_hf(self):
        result = calculate_hf_far("R7-1", 10000)
        assert result["max_far"] == 3.44
        assert result["min_osr"] == 15.5

    def test_all_hf_districts_present(self):
        for district in ["R6", "R7-1", "R7-2", "R8", "R9", "R10"]:
            result = calculate_hf_far(district, 10000)
            assert result["is_height_factor"] is True, f"{district} should be HF"


class TestRequiredOpenSpace:
    """Test minimum open space calculations."""

    def test_r6_required_open_space(self):
        # R6 min OSR = 27.5%
        # For 24,300 SF of floor area: 24300 * 0.275 = 6682.5 SF
        os = get_required_open_space("R6", 24300)
        assert os > 6000

    def test_r10_no_open_space_required(self):
        os = get_required_open_space("R10", 100000)
        assert os == 0

    def test_non_hf_district_no_requirement(self):
        os = get_required_open_space("R7A", 50000)
        assert os == 0


class TestMaxFloorAreaForOpenSpace:
    """Test floor area calculation given open space."""

    def test_r6_max_floor_area(self):
        # With enough open space, should get max FAR
        lot_area = 10000
        # Provide more than minimum open space
        result = get_max_floor_area_for_open_space("R6", lot_area, 0)
        assert result == 10000 * 2.43  # max FAR * lot area

    def test_r10_ignores_open_space(self):
        result = get_max_floor_area_for_open_space("R10", 10000, 5000)
        assert result == 10000 * 10.0
