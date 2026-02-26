"""Tests for FAR lookup tables."""

from __future__ import annotations

import pytest

from app.zoning_engine.far_tables import (
    get_far_for_district,
    get_ih_bonus,
    get_uap_far,
    get_uap_bonus_far,
    UAP_AFFORDABLE_FAR,
    RESIDENTIAL_FAR,
    COMMERCIAL_FAR,
    MANUFACTURING_FAR,
)


class TestResidentialFAR:
    """Test residential district FAR lookups."""

    def test_r1_low_density(self):
        far = get_far_for_district("R1")
        assert far["residential"] == 0.50
        assert far["commercial"] is None
        assert far["cf"] is None

    def test_r4b(self):
        far = get_far_for_district("R4B")
        assert far["residential"] == 0.90
        assert far["cf"] == 2.0

    def test_r5d(self):
        far = get_far_for_district("R5D")
        assert far["residential"] == 2.00
        assert far["cf"] == 2.0

    def test_r6_non_contextual_has_hf_qh(self):
        """R6 without letter suffix should return HF/QH dict.
        QH FAR is street-width dependent: wide=3.0, narrow=2.2.
        """
        far = get_far_for_district("R6")
        assert isinstance(far["residential"], dict)
        assert far["residential"]["hf"] == 0.78
        # QH FAR is street-width dependent
        qh = far["residential"]["qh"]
        assert isinstance(qh, dict)
        assert qh["wide"] == 3.0
        assert qh["narrow"] == 2.2
        assert far["cf"] == 4.8

    def test_r6a_contextual(self):
        """R6A (contextual) should return a single float."""
        far = get_far_for_district("R6A")
        assert far["residential"] == 3.0
        assert far["cf"] == 3.0

    def test_r7a(self):
        far = get_far_for_district("R7A")
        assert far["residential"] == 4.0
        assert far["cf"] == 4.0

    def test_r7x(self):
        far = get_far_for_district("R7X")
        assert far["residential"] == 5.0

    def test_r7_1_non_contextual_street_width_dependent(self):
        """R7-1 QH FAR is street-width dependent: wide=4.0, narrow=3.44."""
        far = get_far_for_district("R7-1")
        assert isinstance(far["residential"], dict)
        assert far["residential"]["hf"] == 0.87
        qh = far["residential"]["qh"]
        assert isinstance(qh, dict)
        assert qh["wide"] == 4.0
        assert qh["narrow"] == 3.44
        assert far["cf"] == 6.5

    def test_r8_non_contextual_street_width_dependent(self):
        """R8 QH FAR is street-width dependent: wide=7.2, narrow=6.02."""
        far = get_far_for_district("R8")
        assert isinstance(far["residential"], dict)
        assert far["residential"]["hf"] == 0.94
        qh = far["residential"]["qh"]
        assert isinstance(qh, dict)
        assert qh["wide"] == 7.2
        assert qh["narrow"] == 6.02

    def test_r8a(self):
        far = get_far_for_district("R8A")
        assert far["residential"] == 6.02

    def test_r10(self):
        far = get_far_for_district("R10")
        assert isinstance(far["residential"], dict)
        assert far["residential"]["qh"] == 10.0
        assert far["cf"] == 10.0

    def test_r10a(self):
        far = get_far_for_district("R10A")
        assert far["residential"] == 10.0

    def test_case_insensitive(self):
        """Should work with any case."""
        far = get_far_for_district("r7a")
        assert far["residential"] == 4.0

    def test_whitespace_handling(self):
        far = get_far_for_district("  R7A  ")
        assert far["residential"] == 4.0


class TestCommercialFAR:
    """Test commercial district FAR lookups."""

    def test_c1_1(self):
        far = get_far_for_district("C1-1")
        assert far["commercial"] == 1.0

    def test_c4_5(self):
        far = get_far_for_district("C4-5")
        assert far["commercial"] == 3.4
        assert far["cf"] == 6.5

    def test_c5_3_midtown(self):
        far = get_far_for_district("C5-3")
        assert far["commercial"] == 15.0

    def test_c6_2_with_residential_equiv(self):
        """C6-2 should have residential FAR from R8 equivalent."""
        far = get_far_for_district("C6-2")
        assert far["commercial"] == 6.0
        assert far["residential"] is not None
        # R8 equivalent has HF/QH dict
        assert isinstance(far["residential"], dict)

    def test_c6_6(self):
        far = get_far_for_district("C6-6")
        assert far["commercial"] == 15.0

    def test_c8_1(self):
        far = get_far_for_district("C8-1")
        assert far["commercial"] == 1.0
        assert far["cf"] == 2.4


class TestManufacturingFAR:
    """Test manufacturing district FAR lookups."""

    def test_m1_1(self):
        far = get_far_for_district("M1-1")
        assert far["manufacturing"] == 1.0
        assert far["commercial"] == 1.0
        assert far["residential"] is None

    def test_m1_6(self):
        far = get_far_for_district("M1-6")
        assert far["manufacturing"] == 10.0

    def test_m2_1_no_commercial(self):
        far = get_far_for_district("M2-1")
        assert far["manufacturing"] == 2.0
        assert far["commercial"] is None

    def test_m3_1(self):
        far = get_far_for_district("M3-1")
        assert far["manufacturing"] == 2.0


class TestUnknownDistricts:
    """Test handling of unknown district codes."""

    def test_unknown_returns_none(self):
        far = get_far_for_district("ZZZZZ")
        assert far["residential"] is None
        assert far["commercial"] is None
        assert far["cf"] is None
        assert far["manufacturing"] is None


class TestIHBonus:
    """Test Inclusionary Housing bonus FAR."""

    def test_r7a_ih_bonus(self):
        bonus = get_ih_bonus("R7A")
        assert bonus is not None
        assert bonus > 0
        assert bonus == pytest.approx(0.6, abs=0.01)

    def test_r10_ih_bonus(self):
        bonus = get_ih_bonus("R10")
        assert bonus is not None
        assert bonus == pytest.approx(2.0, abs=0.01)

    def test_r1_no_ih(self):
        """Low-density districts don't have IH bonus."""
        bonus = get_ih_bonus("R1")
        assert bonus is None

    def test_all_mih_districts_have_positive_bonus(self):
        from app.zoning_engine.far_tables import MIH_BONUS
        for district, vals in MIH_BONUS.items():
            bonus = get_ih_bonus(district)
            assert bonus > 0, f"IH bonus for {district} should be positive"


class TestTableCompleteness:
    """Verify all expected districts are in the tables."""

    def test_all_residential_districts(self):
        expected = [
            "R1", "R2", "R3-1", "R3-2", "R3A", "R3X",
            "R4", "R4A", "R4B",
            "R5", "R5A", "R5B", "R5D",
            "R6", "R6A", "R6B",
            "R7-1", "R7-2", "R7A", "R7B", "R7D", "R7X",
            "R8", "R8A", "R8B", "R8X",
            "R9", "R9A", "R9X",
            "R10", "R10A",
        ]
        for d in expected:
            assert d in RESIDENTIAL_FAR, f"Missing residential district: {d}"

    def test_all_commercial_districts(self):
        expected = [
            "C1-1", "C2-1", "C3", "C4-1", "C5-1", "C6-1", "C7", "C8-1",
        ]
        for d in expected:
            assert d in COMMERCIAL_FAR, f"Missing commercial district: {d}"

    def test_all_manufacturing_districts(self):
        expected = ["M1-1", "M1-2", "M1-3", "M1-4", "M1-5", "M1-6",
                     "M2-1", "M2-2", "M2-3", "M3-1", "M3-2"]
        for d in expected:
            assert d in MANUFACTURING_FAR, f"Missing manufacturing district: {d}"
