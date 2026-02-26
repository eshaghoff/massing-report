"""
NYC Zoning Resolution street wall and lot dimension rules.

STREET WALL (ZR 23-60 series, 35-60 series):
  Quality Housing buildings must maintain a continuous street wall
  at the build-to line for a minimum percentage of the lot frontage.

SLIVER LAW (ZR 23-692):
  Buildings on lots narrower than 45 ft (in R6-R10 non-contextual)
  are limited in height to a multiple of the lot width.
  This prevents excessively tall, thin buildings.

MINIMUM BASE HEIGHT (ZR 23-662):
  In QH districts, the building must rise straight up (no setback)
  from the build-to line to the minimum base height.

MAXIMUM BASE HEIGHT (ZR 23-662):
  Above the maximum base height, the building must set back.
"""

from __future__ import annotations


# ──────────────────────────────────────────────────────────────────
# STREET WALL RULES (Quality Housing, ZR 23-66, 35-65)
# ──────────────────────────────────────────────────────────────────

QH_STREET_WALL = {
    # District: {street_type: {min_pct, max_pct (of frontage at street wall)}}
    # min_pct = minimum % of lot frontage that must be built to street wall
    # setback_distance = distance from street line to building face

    "R6A": {
        "narrow": {"min_base_pct": 60, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R6B": {
        "narrow": {"min_base_pct": 50, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 60, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R7A": {
        "narrow": {"min_base_pct": 60, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R7B": {
        "narrow": {"min_base_pct": 50, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 60, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R7D": {
        "narrow": {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R7X": {
        "narrow": {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R8A": {
        "narrow": {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R8B": {
        "narrow": {"min_base_pct": 60, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 60, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R8X": {
        "narrow": {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R9A": {
        "narrow": {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R9X": {
        "narrow": {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R9D": {
        "narrow": {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R10A": {
        "narrow": {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
    },
    "R10X": {
        "narrow": {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
        "wide":   {"min_base_pct": 70, "max_recess_pct": 30, "setback_distance": 0},
    },
}


# ──────────────────────────────────────────────────────────────────
# SLIVER LAW (ZR 23-692)
# Buildings on narrow lots have height limited to width × factor.
# Applies to: R6 through R10 (non-contextual / Height Factor)
# ──────────────────────────────────────────────────────────────────

SLIVER_LAW_THRESHOLD = 45  # ft — lots narrower than this are subject
SLIVER_LAW_FACTOR = {
    # District: height-to-width multiplier
    # Building height ≤ lot_width × factor
    "R6":   {"factor": 2.7, "max_stories": None},
    "R7-1": {"factor": 3.0, "max_stories": None},
    "R7-2": {"factor": 3.0, "max_stories": None},
    "R8":   {"factor": 3.4, "max_stories": None},
    "R9":   {"factor": 3.7, "max_stories": None},
    "R10":  {"factor": 5.6, "max_stories": None},
}

# Also applies to C districts with residential equivalents
SLIVER_LAW_COMMERCIAL = {
    "C6-1":  "R7-2", "C6-2":  "R8", "C6-3":  "R9", "C6-4":  "R10",
    "C4-3":  "R7-1", "C4-4":  "R8", "C4-5":  "R9", "C4-6":  "R10",
}


def get_sliver_law_height(district: str, lot_width: float) -> float | None:
    """Calculate maximum building height under the Sliver Law.

    ZR 23-692: In non-contextual districts, buildings on lots narrower
    than 45 ft are limited to lot_width × factor in height.

    Args:
        district: Zoning district
        lot_width: Lot frontage width in feet

    Returns:
        Maximum height in feet, or None if sliver law doesn't apply
    """
    if lot_width >= SLIVER_LAW_THRESHOLD:
        return None  # Sliver law doesn't apply

    district = district.strip().upper()

    # Check direct match
    rules = SLIVER_LAW_FACTOR.get(district)

    # Check commercial equivalent
    if not rules:
        equiv = SLIVER_LAW_COMMERCIAL.get(district)
        if equiv:
            rules = SLIVER_LAW_FACTOR.get(equiv)

    if not rules:
        return None  # District not subject to sliver law

    return lot_width * rules["factor"]


def get_street_wall_rules(district: str, street_width: str = "narrow") -> dict:
    """Get street wall requirements for a Quality Housing district.

    Args:
        district: Zoning district
        street_width: "narrow" or "wide"

    Returns dict with:
        applies: bool — whether street wall rules apply
        min_base_pct: minimum % of frontage at street wall
        max_recess_pct: maximum % that can be recessed
        setback_distance: distance from street line (usually 0 in QH)
    """
    district = district.strip().upper()
    width = "wide" if street_width.lower() == "wide" else "narrow"

    rules = QH_STREET_WALL.get(district)
    if not rules:
        return {
            "applies": False,
            "min_base_pct": None,
            "max_recess_pct": None,
            "setback_distance": None,
        }

    r = rules[width]
    return {
        "applies": True,
        "min_base_pct": r["min_base_pct"],
        "max_recess_pct": r["max_recess_pct"],
        "setback_distance": r["setback_distance"],
    }


# ──────────────────────────────────────────────────────────────────
# MINIMUM DWELLING UNIT SIZE (HPD / Building Code / ZR)
# ──────────────────────────────────────────────────────────────────

# NYC Housing Maintenance Code § 27-2074 minimum room sizes
# Plus Zoning Resolution (QH) minimums
MIN_UNIT_SIZES = {
    "studio": {
        "min_total_sf": 400,   # HPD practical minimum
        "min_living_area": 150,
        "min_dimension": 8,     # ft (narrowest dimension)
    },
    "1br": {
        "min_total_sf": 550,
        "min_living_area": 150,
        "min_bedroom": 80,
        "min_dimension": 8,
    },
    "2br": {
        "min_total_sf": 750,
        "min_living_area": 150,
        "min_bedroom": 80,
        "min_dimension": 8,
    },
    "3br": {
        "min_total_sf": 1000,
        "min_living_area": 150,
        "min_bedroom": 80,
        "min_dimension": 8,
    },
}


# ──────────────────────────────────────────────────────────────────
# MINIMUM FLOOR-TO-FLOOR HEIGHTS (Quality Housing, ZR 28-23)
# ──────────────────────────────────────────────────────────────────

QH_MIN_FLOOR_HEIGHTS = {
    # Quality Housing requires minimum floor-to-floor of 9'6" (9.5 ft)
    # for residential floors, and 13' for ground floor commercial
    "residential": 9.5,   # ft floor-to-floor minimum
    "ground_commercial": 13.0,
    "community_facility": 10.0,
}

# Ceiling height minimums (NYC Building Code / Housing Code)
MIN_CEILING_HEIGHTS = {
    "residential": 8.0,     # ft clear ceiling
    "commercial": 8.0,
    "basement": 7.0,        # If used for habitable space (not allowed in zoning)
    "cellar": 7.5,          # If used for certain purposes
}


def get_min_floor_height(district: str, use: str = "residential") -> float:
    """Get minimum floor-to-floor height for a district and use.

    Args:
        district: Zoning district
        use: "residential", "ground_commercial", or "community_facility"

    Returns:
        Minimum floor-to-floor height in feet
    """
    # QH districts have stricter minimums
    if _is_quality_housing(district):
        return QH_MIN_FLOOR_HEIGHTS.get(use, 9.5)

    # Non-QH: building code minimum
    base_heights = {
        "residential": 9.0,        # Typical minimum
        "ground_commercial": 12.0,
        "community_facility": 10.0,
    }
    return base_heights.get(use, 9.0)


def _is_quality_housing(district: str) -> bool:
    """Check if district is a Quality Housing (contextual) district."""
    district = district.strip().upper()
    # QH = has letter suffix (A, B, D, X) on R6+
    import re
    match = re.match(r'^R(\d+)([A-Z])', district)
    if match:
        r_num = int(match.group(1))
        return r_num >= 5  # R5A, R5B, R5D and above are QH
    return False
