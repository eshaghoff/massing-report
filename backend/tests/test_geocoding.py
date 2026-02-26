"""Tests for address parsing (unit tests — no API calls)."""

from __future__ import annotations

import pytest

from app.services.geocoding import parse_address


class TestAddressParsing:
    """Test address parsing into house number, street, and borough."""

    def test_brooklyn_address(self):
        num, street, boro = parse_address("120 Flatbush Ave, Brooklyn")
        assert num == "120"
        assert "Flatbush" in street
        assert boro == 3

    def test_manhattan_address(self):
        num, street, boro = parse_address("350 5th Avenue, Manhattan")
        assert num == "350"
        assert boro == 1

    def test_bronx_address(self):
        num, street, boro = parse_address("1000 Grand Concourse, Bronx")
        assert num == "1000"
        assert boro == 2

    def test_queens_address(self):
        num, street, boro = parse_address("123 Main Street, Queens")
        assert num == "123"
        assert boro == 4

    def test_staten_island_address(self):
        num, street, boro = parse_address("1 Richmond Terrace, Staten Island")
        assert num == "1"
        assert boro == 5

    def test_abbreviations(self):
        _, _, boro = parse_address("120 Flatbush Ave, BK")
        assert boro == 3

    def test_new_york_implies_manhattan(self):
        _, _, boro = parse_address("120 Broadway, New York")
        assert boro == 1

    def test_no_borough_returns_none(self):
        _, _, boro = parse_address("120 Main St")
        assert boro is None

    def test_zipcode_borough_detection(self):
        _, _, boro = parse_address("120 Broadway, NY 10006")
        assert boro == 1

    def test_brooklyn_zipcode(self):
        _, _, boro = parse_address("100 Montague St, NY 11201")
        assert boro == 3
