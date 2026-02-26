"""
NYC Zoning Resolution height, setback, and sky exposure plane rules.

Updated to reflect City of Yes for Housing Opportunity (adopted Dec 5, 2024).

Two regimes:
  1. Quality Housing (QH) — contextual districts (letter suffix): fixed height limits + setbacks
  2. Height Factor (HF) — non-contextual (no suffix): sky exposure plane, no height cap

Street width matters: "wide" = 75+ ft, "narrow" = <75 ft.

The height table now differentiates between:
  - Standard residences (base max height)
  - Qualifying affordable/senior housing (higher max height via UAP)

Sources:
  - ZR Section 23-432 (Quality Housing height limits)
  - ZR Section 23-44 (Sky Exposure Plane)
  - City of Yes for Housing Opportunity amendments (Dec 5, 2024)
"""

from __future__ import annotations

# ──────────────────────────────────────────────────────────────────
# QUALITY HOUSING HEIGHT LIMITS (contextual / letter-suffix districts)
#
# Source: ZR 23-432 as amended by City of Yes (Dec 5, 2024).
#
# The ZR 23-432 table uses footnotes to distinguish narrow/wide,
# and some districts share rows. This table consolidates into a
# per-district, per-street-width structure.
#
# "uap_max_height" is the max height for qualifying affordable
# or senior housing developments under UAP.
#
# All values in feet.
# ──────────────────────────────────────────────────────────────────

QH_HEIGHT_RULES = {
    # ── R4B ──
    "R4B": {
        "narrow": {"base_min": 0, "base_max": 24, "max_height": 24, "setback": 0, "uap_max_height": None},
        "wide":   {"base_min": 0, "base_max": 24, "max_height": 24, "setback": 0, "uap_max_height": None},
    },
    # ── R5 contextual ──
    "R5A": {
        "narrow": {"base_min": 0, "base_max": 25, "max_height": 25, "setback": 0, "uap_max_height": None},
        "wide":   {"base_min": 0, "base_max": 25, "max_height": 25, "setback": 0, "uap_max_height": None},
    },
    "R5B": {
        "narrow": {"base_min": 0, "base_max": 33, "max_height": 33, "setback": 0, "uap_max_height": None},
        "wide":   {"base_min": 0, "base_max": 33, "max_height": 33, "setback": 0, "uap_max_height": None},
    },
    "R5D": {
        "narrow": {"base_min": 25, "base_max": 40, "max_height": 40, "setback": 10, "uap_max_height": None},
        "wide":   {"base_min": 25, "base_max": 40, "max_height": 40, "setback": 10, "uap_max_height": None},
    },
    # ── R6 non-contextual QH option (ZR 23-432) ──
    # Wide street (R6-1): same as R6A = base 40-65, max 75
    # Narrow street (R6-2): base 30-45, max 65
    # These apply when the developer elects the Quality Housing program
    # in a non-contextual R6 district (the alternative to Height Factor).
    "R6": {
        "narrow": {"base_min": 30, "base_max": 45, "max_height": 65,  "setback": 10, "uap_max_height": 85},
        "wide":   {"base_min": 40, "base_max": 65, "max_height": 75,  "setback": 10, "uap_max_height": 95},
    },
    # ── R6A (ZR 23-432: base 40-65, max 75) ──
    "R6A": {
        "narrow": {"base_min": 40, "base_max": 65, "max_height": 75,  "setback": 10, "uap_max_height": 95},
        "wide":   {"base_min": 40, "base_max": 65, "max_height": 75,  "setback": 10, "uap_max_height": 95},
    },
    # ── R6B (ZR 23-432: base 30-45, max 55) ──
    "R6B": {
        "narrow": {"base_min": 30, "base_max": 45, "max_height": 55,  "setback": 10, "uap_max_height": 65},
        "wide":   {"base_min": 30, "base_max": 45, "max_height": 55,  "setback": 10, "uap_max_height": 65},
    },
    # ── R6D (City of Yes new district: base 30-45, max 65) ──
    "R6D": {
        "narrow": {"base_min": 30, "base_max": 45, "max_height": 65,  "setback": 10, "uap_max_height": 75},
        "wide":   {"base_min": 30, "base_max": 45, "max_height": 65,  "setback": 10, "uap_max_height": 75},
    },
    # ── R7-1, R7-2 non-contextual QH option (ZR 23-432) ──
    # Wide street: R7A equivalent height rules
    # Narrow street: lower height limits
    "R7-1": {
        "narrow": {"base_min": 40, "base_max": 65, "max_height": 75,  "setback": 10, "uap_max_height": 95},
        "wide":   {"base_min": 40, "base_max": 75, "max_height": 85,  "setback": 15, "uap_max_height": 115},
    },
    "R7-2": {
        "narrow": {"base_min": 40, "base_max": 65, "max_height": 75,  "setback": 10, "uap_max_height": 95},
        "wide":   {"base_min": 40, "base_max": 75, "max_height": 85,  "setback": 15, "uap_max_height": 115},
    },
    # ── R7A (ZR 23-432: base 40-75, max 85 — increased from 80 under CoY) ──
    "R7A": {
        "narrow": {"base_min": 40, "base_max": 65, "max_height": 75,  "setback": 10, "uap_max_height": 95},
        "wide":   {"base_min": 40, "base_max": 75, "max_height": 85,  "setback": 15, "uap_max_height": 115},
    },
    # ── R7B (ZR 23-432: base 40-65, max 75) ──
    "R7B": {
        "narrow": {"base_min": 40, "base_max": 60, "max_height": 75,  "setback": 10, "uap_max_height": 85},
        "wide":   {"base_min": 40, "base_max": 65, "max_height": 75,  "setback": 10, "uap_max_height": 85},
    },
    # ── R7D (ZR 23-432: base 60-85, max 105) ──
    "R7D": {
        "narrow": {"base_min": 60, "base_max": 85, "max_height": 105, "setback": 10, "uap_max_height": 125},
        "wide":   {"base_min": 60, "base_max": 85, "max_height": 105, "setback": 15, "uap_max_height": 125},
    },
    # ── R7X (ZR 23-432: base 60-95, max 125) ──
    "R7X": {
        "narrow": {"base_min": 60, "base_max": 85, "max_height": 105, "setback": 10, "uap_max_height": 135},
        "wide":   {"base_min": 60, "base_max": 95, "max_height": 125, "setback": 15, "uap_max_height": 155},
    },
    # ── R8 non-contextual QH option (ZR 23-432) ──
    # Wide street: R8A equivalent height rules
    # Narrow street: lower height limits
    "R8": {
        "narrow": {"base_min": 60, "base_max": 85, "max_height": 115, "setback": 10, "uap_max_height": 135},
        "wide":   {"base_min": 60, "base_max": 95, "max_height": 125, "setback": 15, "uap_max_height": 145},
    },
    # ── R8A (ZR 23-432: base 60-95, max 125) ──
    "R8A": {
        "narrow": {"base_min": 60, "base_max": 85, "max_height": 115, "setback": 10, "uap_max_height": 135},
        "wide":   {"base_min": 60, "base_max": 95, "max_height": 125, "setback": 15, "uap_max_height": 145},
    },
    # ── R8B (ZR 23-432: base 55-65, max 75) ──
    "R8B": {
        "narrow": {"base_min": 55, "base_max": 65, "max_height": 75,  "setback": 10, "uap_max_height": 85},
        "wide":   {"base_min": 55, "base_max": 65, "max_height": 75,  "setback": 10, "uap_max_height": 85},
    },
    # ── R8X (ZR 23-432: base 60-95, max 155) ──
    "R8X": {
        "narrow": {"base_min": 60, "base_max": 85, "max_height": 135, "setback": 10, "uap_max_height": 165},
        "wide":   {"base_min": 60, "base_max": 95, "max_height": 155, "setback": 15, "uap_max_height": 175},
    },
    # ── R9 non-contextual QH option (ZR 23-432) ──
    # Same FAR as R9A on both wide and narrow, but QH height rules apply.
    "R9": {
        "narrow": {"base_min": 60, "base_max": 95,  "max_height": 135, "setback": 10, "uap_max_height": 165},
        "wide":   {"base_min": 60, "base_max": 105, "max_height": 145, "setback": 15, "uap_max_height": 175},
    },
    # ── R9A (ZR 23-432: wide max 145, narrow max 135) ──
    "R9A": {
        "narrow": {"base_min": 60, "base_max": 95,  "max_height": 135, "setback": 10, "uap_max_height": 165},
        "wide":   {"base_min": 60, "base_max": 105, "max_height": 145, "setback": 15, "uap_max_height": 175},
    },
    # ── R9X (ZR 23-432: wide max 175, narrow max 165) ──
    "R9X": {
        "narrow": {"base_min": 60,  "base_max": 95,  "max_height": 165, "setback": 10, "uap_max_height": 195},
        "wide":   {"base_min": 105, "base_max": 125, "max_height": 175, "setback": 15, "uap_max_height": 205},
    },
    # ── R9D (ZR 23-432: base 60-125, max 175) ──
    "R9D": {
        "narrow": {"base_min": 60, "base_max": 95,  "max_height": 155, "setback": 10, "uap_max_height": 185},
        "wide":   {"base_min": 60, "base_max": 125, "max_height": 175, "setback": 15, "uap_max_height": 205},
    },
    # ── R10 non-contextual QH option (ZR 23-432) ──
    # Same FAR as R10A on both wide and narrow, but QH height rules apply.
    "R10": {
        "narrow": {"base_min": 60,  "base_max": 125, "max_height": 185, "setback": 10, "uap_max_height": 215},
        "wide":   {"base_min": 125, "base_max": 155, "max_height": 215, "setback": 15, "uap_max_height": 245},
    },
    # ── R10A (ZR 23-432: base 60/125-155, max 185/215) ──
    "R10A": {
        "narrow": {"base_min": 60,  "base_max": 125, "max_height": 185, "setback": 10, "uap_max_height": 215},
        "wide":   {"base_min": 125, "base_max": 155, "max_height": 215, "setback": 15, "uap_max_height": 245},
    },
    # ── R10X (ZR 23-432: base 60/155, max 210/215) ──
    "R10X": {
        "narrow": {"base_min": 60, "base_max": 125, "max_height": 185, "setback": 10, "uap_max_height": 215},
        "wide":   {"base_min": 60, "base_max": 155, "max_height": 215, "setback": 15, "uap_max_height": 245},
    },
}

# ──────────────────────────────────────────────────────────────────
# HEIGHT FACTOR SKY EXPOSURE PLANE (non-contextual R6-R10)
# start_height = height at which SEP starts
# slope = vertical:horizontal ratio (rise:run)
# Source: ZR 23-44
# ──────────────────────────────────────────────────────────────────

SKY_EXPOSURE_PLANE = {
    "R6": {
        "narrow": {"start_height": 60, "slope": 2.7},
        "wide":   {"start_height": 85, "slope": 5.6},
    },
    "R7-1": {
        "narrow": {"start_height": 60, "slope": 2.7},
        "wide":   {"start_height": 85, "slope": 5.6},
    },
    "R7-2": {
        "narrow": {"start_height": 60, "slope": 2.7},
        "wide":   {"start_height": 85, "slope": 5.6},
    },
    "R8": {
        "narrow": {"start_height": 60, "slope": 2.7},
        "wide":   {"start_height": 85, "slope": 5.6},
    },
    "R9": {
        "narrow": {"start_height": 60, "slope": 2.7},
        "wide":   {"start_height": 85, "slope": 5.6},
    },
    "R10": {
        "narrow": {"start_height": 60, "slope": 5.6},
        "wide":   {"start_height": 85, "slope": 5.6},
    },
}

# ──────────────────────────────────────────────────────────────────
# FLOOR-TO-FLOOR HEIGHTS (defaults)
# ──────────────────────────────────────────────────────────────────

FLOOR_HEIGHTS = {
    "ground_commercial": 14,      # ft (13 ft clear + structure)
    "ground_residential": 12,     # ft (non-QH)
    "typical_residential": 10,    # ft (non-QH default)
    "typical_commercial": 13,
    "typical_cf": 12,
    "parking_below_grade": 12,
    "parking_at_grade": 14,
    "mechanical": 12,
}

# Quality Housing floor-to-floor minimums (ZR 23-663)
# QH requires higher floor-to-floor heights than non-QH buildings.
QH_FLOOR_HEIGHTS = {
    "ground_commercial": 14,      # 13 ft clear ceiling required
    "ground_residential": 12,     # 10 ft clear + structure
    "typical_residential": 10.5,  # 9 ft 6 in clear ceiling + structure
    "typical_commercial": 14,
    "typical_cf": 12,
}

# ──────────────────────────────────────────────────────────────────
# PERMITTED OBSTRUCTIONS ABOVE HEIGHT LIMIT (ZR 23-62, 33-42)
# These elements may exceed the maximum building height.
# ──────────────────────────────────────────────────────────────────

PERMITTED_OBSTRUCTIONS = {
    "elevator_bulkhead": {
        "max_height_above_roof": 25,  # ft
        "max_coverage_pct": 20,       # % of lot coverage or roof area
    },
    "stair_bulkhead": {
        "max_height_above_roof": 25,
        "max_coverage_pct": 20,       # Combined with elevator
    },
    "mechanical_equipment": {
        "max_height_above_roof": 25,
        "max_coverage_pct": 20,       # Combined with above
    },
    "water_tank": {
        "max_height_above_roof": 25,
        "max_coverage_pct": 20,
    },
    "parapet_wall": {
        "max_height_above_roof": 4,
    },
    "solar_panels": {
        "max_height_above_roof": 4,   # As-of-right
        "max_coverage_pct": 100,      # No limit
    },
    "flagpole": {
        "max_height_above_roof": None,  # No limit
    },
}

# Total permitted obstruction zone above max height
BULKHEAD_ZONE_HEIGHT = 25  # ft above roof (for elevator/stair/mech)
BULKHEAD_MAX_COVERAGE_PCT = 20  # % of lot coverage


def get_height_rules(
    district: str,
    street_width: str = "narrow",
    is_affordable: bool = False,
    program: str = "auto",
) -> dict:
    """Get height and setback rules for a zoning district.

    Args:
        district: Zoning district code (e.g., "R6A")
        street_width: "narrow" or "wide"
        is_affordable: If True, use UAP affordable housing height bonuses
        program: "auto" (default), "qh" (force Quality Housing), or "hf"
            (force Height Factor). For non-contextual districts that have
            both QH and HF options (R6, R7-1, R7-2, R8, R9, R10),
            "auto" returns QH rules. Use "hf" to get HF/SEP rules.

    Returns dict with keys:
      - quality_housing: bool
      - base_height_min, base_height_max: float
      - max_building_height: float or None (None = no cap, SEP applies)
      - setback_above_base: float
      - sky_exposure_plane: dict or None
    """
    district = district.strip().upper()
    width = "wide" if street_width.lower() == "wide" else "narrow"

    # For non-contextual districts with both programs, check the requested one
    has_both = district in QH_HEIGHT_RULES and district in SKY_EXPOSURE_PLANE
    use_qh = (program != "hf") if has_both else True
    use_hf = (program == "hf") if has_both else False

    # Check Quality Housing (contextual/letter districts, or QH option for non-contextual)
    if district in QH_HEIGHT_RULES and use_qh:
        rules = QH_HEIGHT_RULES[district][width]
        max_ht = rules["max_height"]

        # UAP affordable housing height bonus
        if is_affordable and rules.get("uap_max_height"):
            max_ht = rules["uap_max_height"]

        return {
            "quality_housing": True,
            "height_factor": False,
            "base_height_min": rules["base_min"],
            "base_height_max": rules["base_max"],
            "max_building_height": max_ht,
            "setback_above_base": rules["setback"],
            "sky_exposure_plane": None,
        }

    # Check Height Factor (non-contextual R6-R10)
    if district in SKY_EXPOSURE_PLANE:
        sep = SKY_EXPOSURE_PLANE[district][width]
        return {
            "quality_housing": False,
            "height_factor": True,
            "base_height_min": None,
            "base_height_max": sep["start_height"],
            "max_building_height": None,  # No height cap in HF
            "setback_above_base": 15 if width == "wide" else 10,
            "sky_exposure_plane": {
                "start_height": sep["start_height"],
                "ratio": sep["slope"],
                "direction": "front",
            },
        }

    # Low-density districts (R1-R5 without special suffix)
    low_density_heights = {
        "R1": 35, "R1-1": 35, "R1-2": 35, "R1-2A": 35,
        "R2": 35, "R2A": 35, "R2X": 35,
        "R3-1": 35, "R3-2": 35, "R3A": 35, "R3X": 35,
        "R4": 35, "R4-1": 35, "R4A": 35,
        "R5": 40,
    }
    if district in low_density_heights:
        return {
            "quality_housing": False,
            "height_factor": False,
            "base_height_min": None,
            "base_height_max": None,
            "max_building_height": low_density_heights[district],
            "setback_above_base": 0,
            "sky_exposure_plane": None,
        }

    # R11, R12 high-density (City of Yes): tower regulations apply
    if district in ("R11", "R12"):
        return {
            "quality_housing": False,
            "height_factor": False,
            "base_height_min": 60,
            "base_height_max": 150,
            "max_building_height": None,  # No height cap, tower rules
            "setback_above_base": 15,
            "sky_exposure_plane": None,
        }

    # Commercial districts — map to residential equivalent height rules
    # or use commercial-specific rules
    from app.zoning_engine.far_tables import COMMERCIAL_RESIDENTIAL_EQUIVALENTS
    equiv = COMMERCIAL_RESIDENTIAL_EQUIVALENTS.get(district)
    if equiv:
        return get_height_rules(equiv, street_width, is_affordable)

    # Default fallback
    return {
        "quality_housing": False,
        "height_factor": False,
        "base_height_min": None,
        "base_height_max": None,
        "max_building_height": None,
        "setback_above_base": 0,
        "sky_exposure_plane": None,
    }


def get_floor_heights(is_quality_housing: bool = False) -> dict:
    """Get floor-to-floor heights based on building program.

    QH buildings have stricter minimums per ZR 23-663.

    Returns dict with ground and typical heights for each use type.
    """
    if is_quality_housing:
        return dict(QH_FLOOR_HEIGHTS)
    return dict(FLOOR_HEIGHTS)


def get_bulkhead_allowance(lot_area: float, lot_coverage_pct: float = 100) -> dict:
    """Calculate permitted obstruction zone above the max building height.

    ZR 23-62: Elevator/stair bulkheads, mechanical equipment, and
    water tanks may exceed the max height by up to 25 ft, provided
    their aggregate footprint does not exceed 20% of lot coverage.

    Args:
        lot_area: Lot area in SF
        lot_coverage_pct: Actual lot coverage percentage

    Returns dict with:
        max_height_above_roof: max bulkhead height (25 ft)
        max_bulkhead_sf: maximum aggregate bulkhead footprint
        items: list of permitted obstruction types
    """
    roof_area = lot_area * (lot_coverage_pct / 100)
    max_bulkhead_sf = roof_area * (BULKHEAD_MAX_COVERAGE_PCT / 100)

    return {
        "max_height_above_roof": BULKHEAD_ZONE_HEIGHT,
        "max_bulkhead_sf": round(max_bulkhead_sf),
        "max_coverage_pct": BULKHEAD_MAX_COVERAGE_PCT,
        "parapet_max_height": 4,
        "solar_panel_max_height": 4,
        "items": [
            "Elevator machinery room",
            "Stair bulkhead",
            "Mechanical equipment (HVAC, etc.)",
            "Water tank and enclosure",
        ],
    }
