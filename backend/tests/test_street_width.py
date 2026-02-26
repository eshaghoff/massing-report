"""Tests for street width detection service."""

from __future__ import annotations

import pytest

from app.services.street_width import (
    _parse_street_width,
    is_wide_street_heuristic,
)


class TestParseStreetWidth:
    """Test parsing of DCP Digital City Map streetwidt values."""

    def test_plain_number(self):
        assert _parse_street_width("80") == 80.0

    def test_decimal(self):
        assert _parse_street_width("80.5") == 80.5

    def test_greater_than(self):
        # ">80" -> 80.0 (conservative lower bound)
        assert _parse_street_width(">80") == 80.0

    def test_greater_than_decimal(self):
        assert _parse_street_width(">100.14") == 100.14

    def test_approximately(self):
        assert _parse_street_width("~80") == 80.0

    def test_less_than(self):
        # "<80" -> 79.0 (conservative)
        assert _parse_street_width("<80") == 79.0

    def test_range(self):
        # "80-90" -> 80.0 (minimum of range)
        assert _parse_street_width("80-90") == 80.0

    def test_range_decimal(self):
        assert _parse_street_width("100-185.11") == 100.0

    def test_empty_string(self):
        assert _parse_street_width("") is None

    def test_none(self):
        assert _parse_street_width(None) is None

    def test_whitespace(self):
        assert _parse_street_width("  80  ") == 80.0

    def test_wide_street_threshold_at_75(self):
        assert _parse_street_width("75") == 75.0

    def test_wide_street_threshold_below_75(self):
        assert _parse_street_width("60") == 60.0

    def test_100(self):
        assert _parse_street_width("100") == 100.0

    def test_large_width(self):
        assert _parse_street_width("300") == 300.0

    def test_small_width(self):
        assert _parse_street_width("10") == 10.0


class TestIsWideStreetHeuristic:
    """Test the fallback heuristic for wide street detection."""

    def test_avenue_is_wide(self):
        assert is_wide_street_heuristic("100 5TH AVENUE") is True

    def test_ave_abbreviation_is_wide(self):
        assert is_wide_street_heuristic("100 PARK AVE") is True

    def test_boulevard_is_wide(self):
        assert is_wide_street_heuristic("100 QUEENS BOULEVARD") is True

    def test_broadway_is_wide(self):
        assert is_wide_street_heuristic("100 BROADWAY") is True

    def test_parkway_is_wide(self):
        assert is_wide_street_heuristic("100 OCEAN PARKWAY") is True

    def test_plain_street_not_wide(self):
        assert is_wide_street_heuristic("100 EAST 53 STREET") is False

    def test_plain_numbered_street_not_wide(self):
        assert is_wide_street_heuristic("100 WEST 10 STREET") is False

    def test_known_wide_street_manhattan(self):
        assert is_wide_street_heuristic("100 CANAL STREET", borough=1) is True

    def test_known_wide_street_manhattan_42nd(self):
        assert is_wide_street_heuristic("100 42ND STREET", borough=1) is True

    def test_known_wide_street_bronx(self):
        assert is_wide_street_heuristic("100 FORDHAM ROAD", borough=2) is True

    def test_not_wide_wrong_borough(self):
        # Canal Street is known wide in Manhattan (1), not Brooklyn (3)
        assert is_wide_street_heuristic("100 CANAL STREET", borough=3) is False

    def test_highway_is_wide(self):
        assert is_wide_street_heuristic("100 KINGS HIGHWAY") is True


class TestStreetWidthClassification:
    """Test that parsed widths classify correctly as wide/narrow."""

    @pytest.mark.parametrize("width_str,expected_wide", [
        ("80", True),      # 80 >= 75
        ("75", True),      # 75 >= 75 (exactly at threshold)
        ("60", False),     # 60 < 75
        (">80", True),     # >80 -> 80 >= 75
        ("~90", True),     # ~90 -> 90 >= 75
        ("<75", False),    # <75 -> 74 < 75
        ("<76", True),     # <76 -> 75 >= 75
        ("80-90", True),   # 80-90 -> 80 >= 75
        ("50-60", False),  # 50-60 -> 50 < 75
        ("100", True),     # 100 >= 75
    ])
    def test_width_classification(self, width_str, expected_wide):
        width = _parse_street_width(width_str)
        assert (width >= 75) == expected_wide
