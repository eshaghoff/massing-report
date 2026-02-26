"""Tests for scenario valuation and highest-and-best-use ranking."""

import pytest
from unittest.mock import MagicMock

from app.zoning_engine.valuation import (
    get_value_benchmarks,
    estimate_scenario_value,
    rank_scenarios,
    get_value_disclaimer,
    VALUE_PER_SF,
)


def _make_scenario(
    name="Test Scenario",
    residential_sf=10000,
    commercial_sf=0,
    cf_sf=0,
    parking_sf=0,
    total_gross_sf=None,
):
    """Create a mock DevelopmentScenario with the given SF values."""
    sc = MagicMock()
    sc.name = name
    sc.residential_sf = residential_sf
    sc.commercial_sf = commercial_sf
    sc.cf_sf = cf_sf
    sc.parking_sf = parking_sf
    sc.total_gross_sf = total_gross_sf or (residential_sf + commercial_sf + cf_sf + parking_sf)
    return sc


# ──────────────────────────────────────────────────────────────
# BENCHMARKS
# ──────────────────────────────────────────────────────────────

class TestGetValueBenchmarks:
    def test_manhattan(self):
        rates = get_value_benchmarks(1)
        assert rates["residential"] == 1500
        assert rates["commercial"] == 800
        assert rates["cf"] == 500

    def test_brooklyn(self):
        rates = get_value_benchmarks(3)
        assert rates["residential"] == 1000
        assert rates["commercial"] == 600

    def test_bronx(self):
        rates = get_value_benchmarks(2)
        assert rates["residential"] == 500

    def test_queens(self):
        rates = get_value_benchmarks(4)
        assert rates["residential"] == 700

    def test_staten_island(self):
        rates = get_value_benchmarks(5)
        assert rates["residential"] == 550

    def test_unknown_borough_falls_back_to_brooklyn(self):
        rates = get_value_benchmarks(99)
        assert rates == VALUE_PER_SF[3]

    def test_zero_borough_falls_back(self):
        rates = get_value_benchmarks(0)
        assert rates == VALUE_PER_SF[3]


# ──────────────────────────────────────────────────────────────
# SCENARIO VALUE ESTIMATION
# ──────────────────────────────────────────────────────────────

class TestEstimateScenarioValue:
    def test_pure_residential_manhattan(self):
        sc = _make_scenario(residential_sf=10000, commercial_sf=0, cf_sf=0)
        val = estimate_scenario_value(sc, borough=1)
        assert val["residential_value"] == 10000 * 1500
        assert val["commercial_value"] == 0
        assert val["cf_value"] == 0
        assert val["total_estimated_value"] == 15_000_000

    def test_mixed_use_brooklyn(self):
        sc = _make_scenario(residential_sf=8000, commercial_sf=2000, cf_sf=0)
        val = estimate_scenario_value(sc, borough=3)
        assert val["residential_value"] == 8000 * 1000
        assert val["commercial_value"] == 2000 * 600
        assert val["total_estimated_value"] == 8_000_000 + 1_200_000

    def test_all_uses(self):
        sc = _make_scenario(residential_sf=5000, commercial_sf=3000, cf_sf=2000, parking_sf=1000)
        val = estimate_scenario_value(sc, borough=3)
        expected = 5000 * 1000 + 3000 * 600 + 2000 * 400 + 1000 * 70
        assert val["total_estimated_value"] == expected

    def test_blended_rate(self):
        sc = _make_scenario(residential_sf=10000, total_gross_sf=10000)
        val = estimate_scenario_value(sc, borough=1)
        assert val["value_per_sf_blended"] == 1500.0

    def test_zero_gross_sf(self):
        sc = _make_scenario(residential_sf=0, commercial_sf=0, cf_sf=0, total_gross_sf=0)
        val = estimate_scenario_value(sc, borough=1)
        assert val["total_estimated_value"] == 0
        assert val["value_per_sf_blended"] == 0.0

    def test_rates_included(self):
        sc = _make_scenario(residential_sf=100)
        val = estimate_scenario_value(sc, borough=2)
        assert "rates_used" in val
        assert val["rates_used"]["residential"] == 500


# ──────────────────────────────────────────────────────────────
# RANKING
# ──────────────────────────────────────────────────────────────

class TestRankScenarios:
    def test_empty_list(self):
        assert rank_scenarios([], 1) == []

    def test_single_scenario(self):
        sc = _make_scenario(name="Only One", residential_sf=5000)
        ranked = rank_scenarios([sc], 3)
        assert len(ranked) == 1
        assert ranked[0]["rank"] == 1
        assert ranked[0]["is_highest_best"] is True
        assert ranked[0]["scenario_name"] == "Only One"

    def test_ordering_by_value(self):
        """Higher-value scenario should rank first."""
        small = _make_scenario(name="Small", residential_sf=5000)
        large = _make_scenario(name="Large", residential_sf=20000)
        mid = _make_scenario(name="Mid", residential_sf=10000)

        ranked = rank_scenarios([small, large, mid], borough=3)

        assert ranked[0]["scenario_name"] == "Large"
        assert ranked[0]["rank"] == 1
        assert ranked[0]["is_highest_best"] is True

        assert ranked[1]["scenario_name"] == "Mid"
        assert ranked[1]["rank"] == 2
        assert ranked[1]["is_highest_best"] is False

        assert ranked[2]["scenario_name"] == "Small"
        assert ranked[2]["rank"] == 3

    def test_residential_tiebreak(self):
        """When total value is the same, higher residential SF wins."""
        # Both have $10M total value in Manhattan
        # Scenario A: 5000 res ($7.5M) + 3125 comm ($2.5M) = $10M
        # Scenario B: 6000 res ($9M) + 1250 comm ($1M) = $10M
        # Actually let me compute carefully:
        # Manhattan: res=$1500, comm=$800
        # A: 5000*1500 + 3125*800 = 7,500,000 + 2,500,000 = $10M
        # B: 6000*1500 + 625*800 = 9,000,000 + 500,000 = $9.5M — not equal
        # Let me make them exactly equal:
        # A: 5000*1500 = $7.5M, need $2.5M more from comm: 2500000/800 = 3125 SF comm
        # B: 6000*1500 = $9M, need $1M more from comm: 1000000/800 = 1250 SF comm
        # A total = $10M, B total = $10M → should prefer B (more residential)
        # Wait, 6000*1500 + 1250*800 = 9,000,000 + 1,000,000 = $10M ✓
        a = _make_scenario(name="Less Residential", residential_sf=5000, commercial_sf=3125)
        b = _make_scenario(name="More Residential", residential_sf=6000, commercial_sf=1250)

        ranked = rank_scenarios([a, b], borough=1)
        assert ranked[0]["scenario_name"] == "More Residential"
        assert ranked[1]["scenario_name"] == "Less Residential"

    def test_mixed_use_vs_pure_residential(self):
        """Mixed-use with commercial can beat pure residential."""
        # Brooklyn rates: res=$1000, comm=$600
        pure_res = _make_scenario(name="Pure Res", residential_sf=10000, commercial_sf=0)
        mixed = _make_scenario(name="Mixed", residential_sf=10000, commercial_sf=5000)

        ranked = rank_scenarios([pure_res, mixed], borough=3)
        # Mixed: 10000*1000 + 5000*600 = $13M
        # Pure: 10000*1000 = $10M
        assert ranked[0]["scenario_name"] == "Mixed"

    def test_preserves_scenario_index(self):
        """Scenario index should map back to the original list position."""
        a = _make_scenario(name="A", residential_sf=100)
        b = _make_scenario(name="B", residential_sf=200)
        c = _make_scenario(name="C", residential_sf=300)

        ranked = rank_scenarios([a, b, c], borough=3)
        # C (idx=2) > B (idx=1) > A (idx=0)
        assert ranked[0]["scenario_index"] == 2
        assert ranked[1]["scenario_index"] == 1
        assert ranked[2]["scenario_index"] == 0

    def test_value_fields_present(self):
        sc = _make_scenario(name="Test", residential_sf=1000, commercial_sf=500)
        ranked = rank_scenarios([sc], borough=3)
        entry = ranked[0]
        assert "residential_value" in entry
        assert "commercial_value" in entry
        assert "cf_value" in entry
        assert "total_estimated_value" in entry
        assert "value_per_sf_blended" in entry
        assert "rates_used" in entry


# ──────────────────────────────────────────────────────────────
# DISCLAIMER
# ──────────────────────────────────────────────────────────────

class TestDisclaimer:
    def test_disclaimer_is_string(self):
        assert isinstance(get_value_disclaimer(), str)

    def test_disclaimer_mentions_appraisal(self):
        d = get_value_disclaimer()
        assert "appraisal" in d.lower()

    def test_disclaimer_mentions_benchmark(self):
        d = get_value_disclaimer()
        assert "benchmark" in d.lower()
