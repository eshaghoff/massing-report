"""Tests for height and setback calculator.

Updated to reflect corrected ZR 23-432 values (City of Yes amendments).
"""

from __future__ import annotations

import pytest

from app.zoning_engine.height_setback import get_height_rules, QH_HEIGHT_RULES, SKY_EXPOSURE_PLANE


class TestQualityHousingRules:
    """Test contextual (Quality Housing) district height rules."""

    def test_r6a_narrow(self):
        """R6A narrow: base 40-65, max 75 (ZR 23-432)."""
        rules = get_height_rules("R6A", "narrow")
        assert rules["quality_housing"] is True
        assert rules["height_factor"] is False
        assert rules["base_height_min"] == 40
        assert rules["base_height_max"] == 65
        assert rules["max_building_height"] == 75
        assert rules["setback_above_base"] == 10
        assert rules["sky_exposure_plane"] is None

    def test_r6a_wide(self):
        """R6A wide: same as narrow per ZR 23-432 (single row)."""
        rules = get_height_rules("R6A", "wide")
        assert rules["quality_housing"] is True
        assert rules["max_building_height"] == 75
        assert rules["base_height_max"] == 65

    def test_r7a_narrow(self):
        """R7A narrow: max 75 ft (ZR 23-432)."""
        rules = get_height_rules("R7A", "narrow")
        assert rules["max_building_height"] == 75
        assert rules["base_height_max"] == 65

    def test_r7a_wide(self):
        """R7A wide: max 85 ft (increased from 80 under City of Yes)."""
        rules = get_height_rules("R7A", "wide")
        assert rules["max_building_height"] == 85
        assert rules["setback_above_base"] == 15

    def test_r7a_affordable_height_bonus(self):
        """R7A with UAP: max 115 ft on wide street (City of Yes)."""
        rules = get_height_rules("R7A", "wide", is_affordable=True)
        assert rules["max_building_height"] == 115

    def test_r8a_wide(self):
        """R8A wide: max 125 ft (ZR 23-432)."""
        rules = get_height_rules("R8A", "wide")
        assert rules["max_building_height"] == 125
        assert rules["base_height_max"] == 95

    def test_r8b_narrow(self):
        """R8B: max 75 ft (corrected from 100)."""
        rules = get_height_rules("R8B", "narrow")
        assert rules["max_building_height"] == 75
        assert rules["base_height_max"] == 65

    def test_r9a_wide(self):
        """R9A wide: max 145 ft (ZR 23-432)."""
        rules = get_height_rules("R9A", "wide")
        assert rules["max_building_height"] == 145

    def test_r10a_wide(self):
        """R10A wide: max 215 ft (ZR 23-432)."""
        rules = get_height_rules("R10A", "wide")
        assert rules["max_building_height"] == 215

    def test_r4b_low_max(self):
        rules = get_height_rules("R4B", "narrow")
        assert rules["max_building_height"] == 24

    def test_wide_always_higher_or_equal(self):
        """Wide street height limits should be >= narrow street limits."""
        for district in QH_HEIGHT_RULES:
            narrow = get_height_rules(district, "narrow")
            wide = get_height_rules(district, "wide")
            assert wide["max_building_height"] >= narrow["max_building_height"], \
                f"{district}: wide ({wide['max_building_height']}) < narrow ({narrow['max_building_height']})"

    def test_uap_height_always_higher_or_equal(self):
        """UAP affordable height should be >= standard height."""
        for district in QH_HEIGHT_RULES:
            for width in ("narrow", "wide"):
                standard = get_height_rules(district, width, is_affordable=False)
                affordable = get_height_rules(district, width, is_affordable=True)
                assert affordable["max_building_height"] >= standard["max_building_height"], \
                    f"{district} {width}: affordable height should be >= standard"


class TestHeightFactorRules:
    """Test non-contextual (Height Factor) district rules."""

    def test_r6_defaults_to_qh(self):
        """R6 defaults to Quality Housing (not HF) since it's in both tables."""
        rules = get_height_rules("R6", "narrow")
        assert rules["quality_housing"] is True
        assert rules["height_factor"] is False
        assert rules["max_building_height"] == 65  # R6 QH narrow = 65 ft
        assert rules["sky_exposure_plane"] is None

    def test_r6_qh_wide(self):
        """R6 QH wide: base 40-65, max 75 (same as R6A)."""
        rules = get_height_rules("R6", "wide")
        assert rules["quality_housing"] is True
        assert rules["max_building_height"] == 75
        assert rules["base_height_max"] == 65

    def test_r6_height_factor_explicit(self):
        """R6 HF (explicit program='hf'): no height cap, SEP applies."""
        rules = get_height_rules("R6", "narrow", program="hf")
        assert rules["quality_housing"] is False
        assert rules["height_factor"] is True
        assert rules["max_building_height"] is None  # No height cap
        assert rules["sky_exposure_plane"] is not None
        assert rules["sky_exposure_plane"]["start_height"] == 60

    def test_r7_1_defaults_to_qh(self):
        """R7-1 defaults to QH (not HF) since it's in both tables."""
        rules = get_height_rules("R7-1", "narrow")
        assert rules["quality_housing"] is True
        assert rules["max_building_height"] == 75

    def test_r7_1_qh_wide(self):
        """R7-1 QH wide: same as R7A = max 85 ft."""
        rules = get_height_rules("R7-1", "wide")
        assert rules["quality_housing"] is True
        assert rules["max_building_height"] == 85

    def test_r8_defaults_to_qh(self):
        """R8 defaults to QH (not HF) since it's in both tables."""
        rules = get_height_rules("R8", "wide")
        assert rules["quality_housing"] is True
        assert rules["max_building_height"] == 125

    def test_r8_height_factor_explicit(self):
        """R8 HF (explicit): no height cap, SEP applies."""
        rules = get_height_rules("R8", "wide", program="hf")
        assert rules["height_factor"] is True
        assert rules["sky_exposure_plane"]["start_height"] == 85
        assert rules["sky_exposure_plane"]["ratio"] == 5.6

    def test_r9_defaults_to_qh(self):
        """R9 defaults to QH."""
        rules = get_height_rules("R9", "wide")
        assert rules["quality_housing"] is True
        assert rules["max_building_height"] == 145

    def test_r10_defaults_to_qh(self):
        """R10 defaults to QH."""
        rules = get_height_rules("R10", "narrow")
        assert rules["quality_housing"] is True
        assert rules["max_building_height"] == 185

    def test_r10_height_factor_explicit(self):
        """R10 HF (explicit): no height cap, SEP applies."""
        rules = get_height_rules("R10", "narrow", program="hf")
        assert rules["height_factor"] is True
        assert rules["sky_exposure_plane"]["ratio"] == 5.6

    def test_all_hf_districts_have_sep(self):
        for district in SKY_EXPOSURE_PLANE:
            # For districts with both QH and HF options (e.g. R6),
            # must explicitly request HF program to get SEP rules.
            rules = get_height_rules(district, "narrow", program="hf")
            assert rules["sky_exposure_plane"] is not None, \
                f"{district} should have sky exposure plane when program='hf'"


class TestLowDensityRules:
    """Test low-density district height limits."""

    def test_r1(self):
        rules = get_height_rules("R1", "narrow")
        assert rules["max_building_height"] == 35
        assert rules["quality_housing"] is False
        assert rules["height_factor"] is False

    def test_r5(self):
        rules = get_height_rules("R5", "narrow")
        assert rules["max_building_height"] == 40

    def test_r3a(self):
        rules = get_height_rules("R3A", "narrow")
        assert rules["max_building_height"] == 35


class TestNewDistricts:
    """Test City of Yes new districts."""

    def test_r6d_height(self):
        rules = get_height_rules("R6D", "narrow")
        assert rules["quality_housing"] is True
        assert rules["max_building_height"] == 65

    def test_r11_no_height_cap(self):
        rules = get_height_rules("R11", "narrow")
        assert rules["max_building_height"] is None

    def test_r12_no_height_cap(self):
        rules = get_height_rules("R12", "narrow")
        assert rules["max_building_height"] is None


class TestCommercialHeightRules:
    """Test commercial district height resolution via equivalents."""

    def test_c6_2_uses_r8_equiv(self):
        """C6-2 maps to R8 for height rules."""
        rules = get_height_rules("C6-2", "narrow")
        r8_rules = get_height_rules("R8", "narrow")
        # Should match R8 rules
        assert rules["height_factor"] == r8_rules["height_factor"]

    def test_c4_4a_uses_r7a_equiv(self):
        rules = get_height_rules("C4-4A", "narrow")
        r7a_rules = get_height_rules("R7A", "narrow")
        assert rules["max_building_height"] == r7a_rules["max_building_height"]
