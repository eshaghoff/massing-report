"""
NYC Zoning Resolution building type rules.

Low-density districts (R1-R5) have specific building type requirements
that determine building form and placement on the lot.

ZR 22-10 through 22-15: Types of Residences
ZR 23-40 through 23-47: Yard and lot coverage by building type

Building types:
  - Detached: free-standing on all sides (R1, R2)
  - Semi-detached: attached on one side (R3, R4)
  - Row/attached: attached on both sides (R4B, R5)
  - Tower-on-base: podium + setback tower (R9, R10)
  - Tower: freestanding tower (R10, some C6)

Each type has different:
  - Side yard requirements
  - Lot coverage limits
  - Building width/depth constraints
  - Minimum lot area and width per unit
"""

from __future__ import annotations


# ──────────────────────────────────────────────────────────────────
# BUILDING TYPE DEFINITIONS AND REQUIREMENTS
# ──────────────────────────────────────────────────────────────────

BUILDING_TYPES = {
    # ─── Detached (ZR 23-44) ───
    "detached": {
        "description": "Single-family detached house, free-standing on all sides",
        "districts": ["R1", "R1-1", "R1-2", "R1-2A", "R2", "R2A", "R2X"],
        "required_side_yards": 2,
        "min_side_yard_each": {
            "R1": 8, "R1-1": 8, "R1-2": 15, "R1-2A": 10,
            "R2": 5, "R2A": 5, "R2X": 5,
        },
        "max_building_width_pct": None,  # No specific width limit
        "lot_coverage": {
            "R1": 35, "R1-1": 35, "R1-2": 25, "R1-2A": 30,
            "R2": 40, "R2A": 40, "R2X": 40,
        },
        "min_lot_area": {
            "R1": 9500, "R1-1": 5700, "R1-2": 5700, "R1-2A": 5700,
            "R2": 3800, "R2A": 2850, "R2X": 3325,
        },
        "min_lot_width": {
            "R1": 100, "R1-1": 60, "R1-2": 60, "R1-2A": 60,
            "R2": 40, "R2A": 30, "R2X": 35,
        },
        "max_stories": {"R1": 2, "R2": 2, "default": 3},
    },

    # ─── Semi-detached (ZR 23-45) ───
    "semi_detached": {
        "description": "Attached on one side, detached on the other",
        "districts": ["R3-1", "R3-2", "R3A", "R3X", "R4-1", "R4A"],
        "required_side_yards": 1,  # One side attached, one side yard
        "min_side_yard": {
            "R3-1": 5, "R3-2": 5, "R3A": 5, "R3X": 5,
            "R4-1": 5, "R4A": 5,
        },
        "lot_coverage": {
            "R3-1": 35, "R3-2": 35, "R3A": 35, "R3X": 35,
            "R4-1": 55, "R4A": 55,
        },
        "min_lot_area": {
            "R3-1": 3800, "R3-2": 1700, "R3A": 2375, "R3X": 2375,
            "R4-1": 2375, "R4A": 2375,
        },
        "min_lot_width": {
            "R3-1": 40, "R3-2": 25, "R3A": 25, "R3X": 25,
            "R4-1": 25, "R4A": 25,
        },
        "max_stories": {"default": 3},
    },

    # ─── Attached / Row house (ZR 23-46) ───
    "attached": {
        "description": "Attached on both sides (rowhouse / townhouse)",
        "districts": ["R4B", "R5", "R5A", "R5B"],
        "required_side_yards": 0,  # No side yards (attached both sides)
        "lot_coverage": {
            "R4B": 55, "R5": 55, "R5A": 55, "R5B": 55,
        },
        "min_lot_area": {
            "R4B": 1700, "R5": 1700, "R5A": 1700, "R5B": 1700,
        },
        "min_lot_width": {
            "R4B": 18, "R5": 18, "R5A": 18, "R5B": 18,
        },
        "max_stories": {"R4B": 3, "R5": 3, "default": 3},
        "max_height_ft": {"R4B": 24},
    },

    # ─── Multi-family / Apartment (medium-high density) ───
    "apartment": {
        "description": "Multi-family apartment building (6+ stories typical)",
        "districts": ["R6", "R6A", "R6B", "R7-1", "R7-2", "R7A", "R7B",
                       "R7D", "R7X", "R8", "R8A", "R8B", "R8X"],
        "required_side_yards": 0,
        "lot_coverage": {
            "R6A": 65, "R6B": 65, "R7A": 65, "R7B": 65,
            "R7D": 65, "R7X": 65, "R8A": 70, "R8B": 70, "R8X": 70,
        },
        "min_lot_width": {"default": 18},
    },

    # ─── Tower-on-base (ZR 23-65, 35-65) ───
    "tower_on_base": {
        "description": "Podium base at street wall + setback tower above",
        "districts": ["R9", "R9A", "R9X", "R9D", "R10", "R10A", "R10X",
                       "C6-4", "C6-4A", "C6-4M", "C6-4X", "C6-5",
                       "C6-5.5", "C6-6", "C6-6.5", "C6-7", "C6-9"],
        "tower_coverage_max": {
            # Maximum % of lot the tower portion can cover
            "R9": 40, "R9A": 40, "R9X": 40, "R9D": 40,
            "R10": 40, "R10A": 40, "R10X": 40,
            "C6-4": 40, "C6-5": 40, "C6-6": 40, "C6-7": 40, "C6-9": 40,
            "default": 40,
        },
        "base_lot_coverage": {
            # Max % of lot covered by the base/podium
            "R9": 100, "R9A": 70, "R10": 100, "R10A": 70,
            "default": 70,
        },
        "base_height_max": {
            # Max base/podium height before setback to tower
            "R9": 85, "R9A": 95, "R10": 85, "R10A": 150,
            "default": 85,
        },
        "tower_setback_from_base": {
            # How far tower must set back from base wall
            "default": 10,
        },
        "min_distance_between_towers": 60,  # ft (ZR 23-663)
        "min_tower_floor_area": 3000,  # SF per floor minimum
    },

    # ─── Freestanding tower (C5, high-density commercial) ───
    "tower": {
        "description": "Freestanding tower, typically with plaza",
        "districts": ["C5-1", "C5-2", "C5-2.5", "C5-3", "C5-5", "C5-P"],
        "tower_coverage_max": {"default": 40},
        "setback_from_lot_line": {"default": 15},
        "plaza_bonus": True,
    },
}


# ──────────────────────────────────────────────────────────────────
# MINIMUM LOT AREA AND WIDTH PER DWELLING UNIT (ZR 23-22 through 23-32)
# ──────────────────────────────────────────────────────────────────

MIN_LOT_AREA_PER_DU = {
    "R1":    9500, "R1-1":  5700, "R1-2":  3800, "R1-2A": 5700,
    "R2":    3800, "R2A":   2850, "R2X":   3325,
    "R3-1":  3800, "R3-2":  1700, "R3A":   2375, "R3X":   2375,
    "R4":    970,  "R4-1":  970,  "R4A":   970,  "R4B":   855,
    "R5":    680,  "R5A":   605,  "R5B":   495,  "R5D":   335,
    # R6+ use dwelling unit factor (ZR 23-52) instead
}


# ──────────────────────────────────────────────────────────────────
# DWELLING UNIT FACTOR (ZR 23-52)
#
# For R6-R12 districts, the maximum number of dwelling units is:
#   max_du = max_residential_floor_area / dwelling_unit_factor
#
# Rounding: fractions ≥ 0.75 round UP to 1 unit; fractions < 0.75 are dropped.
#
# Exemptions (no DU factor applies — unlimited density relative to FAR):
#   - Developments in special density areas
#   - Qualifying senior housing
#   - Conversions of non-residential or CF buildings to residences
#
# Source: ZR 23-52 as amended
# ──────────────────────────────────────────────────────────────────

DWELLING_UNIT_FACTOR = 680  # SF of floor area per dwelling unit (all R6-R12)

MIN_LOT_WIDTH = {
    "R1":    100, "R1-1":  60, "R1-2":  60, "R1-2A": 60,
    "R2":    40,  "R2A":   30, "R2X":   35,
    "R3-1":  40,  "R3-2":  25, "R3A":   25, "R3X":   25,
    "R4":    25,  "R4-1":  25, "R4A":   25, "R4B":   18,
    "R5":    18,  "R5A":   18, "R5B":   18, "R5D":   18,
}


def get_building_type_for_district(district: str) -> str:
    """Determine the appropriate building type for a district.

    Returns: building type key from BUILDING_TYPES
    """
    district = district.strip().upper()

    for btype, config in BUILDING_TYPES.items():
        if district in config.get("districts", []):
            return btype

    # Default based on district prefix
    if district.startswith("R1") or district.startswith("R2"):
        return "detached"
    if district.startswith("R3"):
        return "semi_detached"
    if district.startswith("R4") or district.startswith("R5"):
        return "attached"
    if district.startswith(("R9", "R10")):
        return "tower_on_base"
    if district.startswith(("R6", "R7", "R8")):
        return "apartment"
    if district.startswith("C5"):
        return "tower"
    if district.startswith("C6"):
        if any(d in district for d in ["4", "5", "6", "7", "9"]):
            return "tower_on_base"
        return "apartment"

    return "apartment"


def get_building_type_rules(district: str) -> dict:
    """Get detailed building type rules for a district."""
    district = district.strip().upper()
    btype = get_building_type_for_district(district)
    config = BUILDING_TYPES.get(btype, {})

    result = {
        "building_type": btype,
        "description": config.get("description", ""),
    }

    # Side yards
    result["required_side_yards"] = config.get("required_side_yards", 0)
    if btype == "detached":
        result["min_side_yard"] = config.get("min_side_yard_each", {}).get(district, 5)
    elif btype == "semi_detached":
        result["min_side_yard"] = config.get("min_side_yard", {}).get(district, 5)
    else:
        result["min_side_yard"] = 0

    # Lot coverage
    coverage = config.get("lot_coverage", {})
    result["lot_coverage_max"] = coverage.get(district, coverage.get("default"))

    # Min lot area per DU
    result["min_lot_area_per_du"] = MIN_LOT_AREA_PER_DU.get(district)
    result["min_lot_width"] = MIN_LOT_WIDTH.get(district, config.get("min_lot_width", {}).get("default"))

    # Max units from lot area
    min_area = result["min_lot_area_per_du"]
    result["max_units_by_lot_area"] = None  # Determined by FAR in higher density

    # Tower rules
    if btype in ("tower_on_base", "tower"):
        tower_cov = config.get("tower_coverage_max", {})
        result["tower_coverage_max"] = tower_cov.get(district, tower_cov.get("default", 40))

        base_cov = config.get("base_lot_coverage", {})
        result["base_lot_coverage"] = base_cov.get(district, base_cov.get("default", 70))

        base_ht = config.get("base_height_max", {})
        result["base_height_max"] = base_ht.get(district, base_ht.get("default", 85))

        tower_sb = config.get("tower_setback_from_base", {})
        result["tower_setback"] = tower_sb.get(district, tower_sb.get("default", 10))

        result["min_tower_floor_area"] = config.get("min_tower_floor_area", 3000)
        result["min_distance_between_towers"] = config.get("min_distance_between_towers", 60)

    return result


def get_max_units_by_lot_area(district: str, lot_area: float) -> int | None:
    """For low-density districts, calculate max units based on lot area per DU.

    Returns None if district uses FAR instead of lot-area-per-DU.
    """
    district = district.strip().upper()
    min_area = MIN_LOT_AREA_PER_DU.get(district)
    if min_area is None or min_area <= 0:
        return None  # Uses FAR, not lot area per DU
    return max(1, int(lot_area / min_area))


def get_max_units_by_du_factor(
    district: str,
    max_residential_floor_area: float,
    is_senior_housing: bool = False,
    is_conversion: bool = False,
) -> int | None:
    """For R6-R12 districts, calculate max dwelling units using the DU factor.

    ZR 23-52: Maximum number of DUs = max_residential_floor_area / 680.
    Fractions ≥ 0.75 round up to 1; fractions < 0.75 are dropped.

    Args:
        district: Zoning district code
        max_residential_floor_area: Maximum permitted residential floor area (ZFA)
        is_senior_housing: If True, DU factor does not apply (unlimited)
        is_conversion: If True, DU factor does not apply (unlimited)

    Returns:
        Maximum number of dwelling units, or None if DU factor
        does not apply to this district (R1-R5 use lot area per DU instead).
    """
    district = district.strip().upper()

    # DU factor only applies to R6+ (and equivalent commercial districts)
    import re
    match = re.match(r'^R(\d+)', district)
    if match:
        r_num = int(match.group(1))
        if r_num < 6:
            return None  # R1-R5 use lot area per DU, not DU factor
    elif not district.startswith(("C4", "C5", "C6")):
        return None  # Manufacturing or low-density commercial

    # Exemptions: no DU factor for senior housing or conversions
    if is_senior_housing or is_conversion:
        return None  # Unlimited (constrained only by FAR + building code)

    if max_residential_floor_area <= 0:
        return 0

    raw = max_residential_floor_area / DWELLING_UNIT_FACTOR
    whole = int(raw)
    fraction = raw - whole

    # ZR 23-52: fractions ≥ 0.75 round up
    if fraction >= 0.75:
        return whole + 1
    return max(1, whole)


def calculate_tower_footprint(
    lot_area: float,
    district: str,
    lot_frontage: float = 50,
    lot_depth: float = 100,
) -> dict:
    """Calculate tower-on-base parameters.

    Returns base footprint, tower footprint, and tower floor area.
    """
    rules = get_building_type_rules(district)
    btype = rules["building_type"]

    if btype not in ("tower_on_base", "tower"):
        return {"is_tower": False}

    tower_cov_pct = rules.get("tower_coverage_max", 40) / 100
    base_cov_pct = rules.get("base_lot_coverage", 70) / 100
    tower_setback = rules.get("tower_setback", 10)

    base_footprint = lot_area * base_cov_pct
    tower_footprint = lot_area * tower_cov_pct

    # Tower must be set back from base
    # Estimate tower dimensions assuming roughly square
    tower_side = tower_footprint ** 0.5
    tower_width = min(tower_side, lot_frontage - 2 * tower_setback)
    tower_depth = tower_footprint / tower_width if tower_width > 0 else 0
    tower_actual = tower_width * tower_depth

    return {
        "is_tower": True,
        "building_type": btype,
        "base_footprint_sf": round(base_footprint),
        "tower_footprint_sf": round(tower_actual),
        "tower_coverage_pct": round(tower_actual / lot_area * 100, 1) if lot_area > 0 else 0,
        "base_height_max": rules.get("base_height_max", 85),
        "tower_setback": tower_setback,
        "tower_width": round(tower_width, 1),
        "tower_depth": round(tower_depth, 1),
        "min_tower_floor_area": rules.get("min_tower_floor_area", 3000),
    }
