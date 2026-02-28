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

# Non-contextual districts subject to the sliver law (ZR 23-692)
SLIVER_LAW_DISTRICTS = {
    "R6", "R7-1", "R7-2", "R8", "R9", "R10",
}

# Commercial districts with residential equivalents subject to sliver law
SLIVER_LAW_COMMERCIAL = {
    "C6-1":  "R7-2", "C6-2":  "R8", "C6-3":  "R9", "C6-4":  "R10",
    "C4-3":  "R7-1", "C4-4":  "R8", "C4-5":  "R9", "C4-6":  "R10",
}


def get_sliver_law_height(
    district: str,
    lot_width: float,
    street_width_ft: float | None = None,
    lot_type: str = "interior",
) -> float | None:
    """Calculate maximum building height under the Sliver Law.

    ZR 23-692: In non-contextual R6-R10 districts, buildings with street
    walls less than 45 ft in width are limited in height:
      (a) Interior/through lots: lesser of street width or 100 ft
      (b) Corner lots (narrow streets only): width of narrowest street
      (c) Corner lots (at least one wide street): lesser of widest
          street width or 100 ft

    Args:
        district: Zoning district
        lot_width: Lot frontage / street wall width in feet
        street_width_ft: Actual mapped street width in feet
        lot_type: "interior", "corner", or "through"

    Returns:
        Maximum height in feet, or None if sliver law doesn't apply
    """
    if lot_width >= SLIVER_LAW_THRESHOLD:
        return None  # Sliver law doesn't apply to wide street walls

    district = district.strip().upper()

    # Check if district is subject to sliver law
    is_sliver_district = district in SLIVER_LAW_DISTRICTS
    if not is_sliver_district:
        equiv = SLIVER_LAW_COMMERCIAL.get(district)
        if not equiv:
            return None  # District not subject to sliver law

    # Use actual street width if available, otherwise estimate
    if street_width_ft is None:
        # Fallback: assume 60ft for narrow, 80ft for wide
        street_width_ft = 60.0

    if lot_type == "corner":
        # Corner lot rules depend on whether at least one street is wide
        # We only have one street width — assume this is the primary street.
        # ZR 23-692(b): narrow streets only → narrowest street width
        # ZR 23-692(c): at least one wide street → min(widest, 100)
        if street_width_ft >= 75:
            # At least one wide street
            return min(street_width_ft, 100.0)
        else:
            # Only narrow streets — use narrowest (= the one we know)
            return street_width_ft
    else:
        # Interior and through lots: ZR 23-692(a)
        return min(street_width_ft, 100.0)


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
