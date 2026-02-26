"""
NYC Zoning Resolution yard requirements.

Yard requirements vary by zoning district, lot type, and building type.
"""

from __future__ import annotations


def get_yard_requirements(
    district: str,
    lot_type: str = "interior",
    lot_depth: float = 100,
    lot_frontage: float = 50,
    street_width: str = "narrow",
) -> dict:
    """Calculate yard requirements for a zoning district.

    Args:
        district: Zoning district code (e.g., "R6A")
        lot_type: "interior", "corner", "through", or "irregular"
        lot_depth: Lot depth in feet
        lot_frontage: Lot frontage in feet
        street_width: "narrow" or "wide"

    Returns dict with:
        front_yard, rear_yard, rear_yard_equivalent,
        side_yards_required, side_yard_each, side_yard_total,
        lot_coverage_max
    """
    district = district.strip().upper()
    base = _get_base_district(district)

    result = {
        "front_yard": 0,
        "rear_yard": 30,
        "rear_yard_equivalent": 0,
        "side_yards_required": False,
        "side_yard_each": 0,
        "side_yard_total": 0,
        "lot_coverage_max": None,
    }

    # Determine building type for yard applicability
    # R4/R5 attached buildings (row houses) have NO side yards (party walls)
    # and typically build to the prevailing street line (no front yard)
    from app.zoning_engine.building_types import get_building_type_for_district
    btype = get_building_type_for_district(district)
    is_attached = btype == "attached"

    # Front yard
    if base in ("R1", "R2", "R3"):
        result["front_yard"] = _get_front_yard(district)
    elif base in ("R4", "R5") and not is_attached:
        # Detached / semi-detached in R4/R5 need front yard
        result["front_yard"] = _get_front_yard(district)
    # Attached R4/R5 and higher-density districts: build to street line (no front yard)

    # Rear yard
    result["rear_yard"] = _get_rear_yard(district, lot_depth)

    # Through lots: rear yard equivalent (ZR 23-532, 23-533)
    # A through lot extends from one street to the parallel street.
    # Instead of two rear yards, a central open area is required.
    if lot_type == "through":
        if lot_depth <= 110:
            # Short through lots: treat as two separate buildings, no rear yard equiv
            result["rear_yard_equivalent"] = 0
        elif lot_depth > 180:
            # Deep through lots: 60 ft open area in the center
            result["rear_yard_equivalent"] = 60
        else:
            # Standard through lots: 40 ft open area in the center
            result["rear_yard_equivalent"] = 40
        result["rear_yard"] = 0

    # Side yards
    # R4/R5 attached buildings share party walls — no side yards
    # R1-R3 and detached/semi-detached R4/R5 require side yards
    if base in ("R1", "R2", "R3"):
        result["side_yards_required"] = True
        result["side_yard_each"] = _get_side_yard(district)
        result["side_yard_total"] = result["side_yard_each"] * 2
    elif base in ("R4", "R5") and not is_attached:
        result["side_yards_required"] = True
        result["side_yard_each"] = _get_side_yard(district)
        result["side_yard_total"] = result["side_yard_each"] * 2
    elif lot_type == "corner":
        # Corner lots in some districts require a side yard along the short street
        result["side_yards_required"] = False

    # Lot coverage
    result["lot_coverage_max"] = _get_lot_coverage(district, lot_type)

    return result


def _get_base_district(district: str) -> str:
    """Extract the base district category (R1-R10, C, M)."""
    import re
    match = re.match(r'^(R\d+|C\d+|M\d+)', district)
    if match:
        return match.group(1)
    return district


def _get_front_yard(district: str) -> float:
    """Front yard depth in feet."""
    base = _get_base_district(district)
    front_yards = {
        "R1": 20, "R2": 20, "R3": 15, "R4": 10, "R5": 10,
    }
    return front_yards.get(base, 0)


def _get_rear_yard(district: str, lot_depth: float) -> float:
    """Rear yard depth in feet."""
    base = _get_base_district(district)

    # Most residential: 30 ft or 20% of lot depth, whichever is less
    # but minimum 20 ft in higher-density districts
    if base in ("R1", "R2", "R3", "R4", "R5"):
        return 30
    if base in ("R6", "R7", "R8", "R9", "R10"):
        return min(30, max(20, lot_depth * 0.20))

    # Commercial districts
    if base.startswith("C"):
        if base in ("C1", "C2", "C3"):
            return 20  # local commercial
        return min(20, lot_depth * 0.20)

    # Manufacturing
    if base.startswith("M"):
        return 0  # No rear yard required

    return 30


def _get_side_yard(district: str) -> float:
    """Side yard width per side in feet."""
    # Detached: two side yards required
    # Semi-detached: one side yard
    # Low-density defaults
    side_yards = {
        "R1": 8, "R1-1": 8, "R1-2": 15, "R1-2A": 15,
        "R2": 5, "R2A": 5, "R2X": 5,
        "R3-1": 5, "R3-2": 5, "R3A": 5, "R3X": 5,
        "R4": 5, "R4-1": 5, "R4A": 5, "R4B": 5,
        "R5": 5, "R5A": 5, "R5B": 5, "R5D": 0,
    }
    return side_yards.get(district.strip().upper(), 0)


def _get_lot_coverage(district: str, lot_type: str) -> float | None:
    """Max lot coverage as a percentage. None means no specific limit."""
    district = district.strip().upper()
    base = _get_base_district(district)

    # Quality Housing lot coverage rules
    qh_coverage = {
        # R6 contextual
        "R6A":  {"interior": 65, "corner": 80},
        "R6B":  {"interior": 65, "corner": 80},
        # R7 contextual
        "R7A":  {"interior": 65, "corner": 80},
        "R7B":  {"interior": 65, "corner": 80},
        "R7D":  {"interior": 65, "corner": 80},
        "R7X":  {"interior": 65, "corner": 80},
        # R8 contextual
        "R8A":  {"interior": 70, "corner": 100},
        "R8B":  {"interior": 70, "corner": 100},
        "R8X":  {"interior": 70, "corner": 100},
        # R9-R10 contextual
        "R9A":  {"interior": 70, "corner": 100},
        "R9X":  {"interior": 70, "corner": 100},
        "R9D":  {"interior": 70, "corner": 100},
        "R10A": {"interior": 70, "corner": 100},
        "R10X": {"interior": 70, "corner": 100},
    }

    if district in qh_coverage:
        if lot_type == "corner":
            return qh_coverage[district].get("corner", 80)
        return qh_coverage[district].get("interior", 65)

    # Low-density lot coverage
    low_density = {
        "R1": 35, "R2": 40, "R3": 35, "R4": 55, "R5": 55,
    }
    if base in low_density:
        return low_density[base]

    # Medium/high-density non-contextual districts (R6-R10 base)
    # These districts have lot coverage limits under Quality Housing (ZR 23-15).
    # R6-R7: 65% interior, 80% corner
    # R8-R10: 70% interior, 100% corner
    medium_high_density = {
        "R6":  {"interior": 65, "corner": 80},
        "R7":  {"interior": 65, "corner": 80},
        "R8":  {"interior": 70, "corner": 100},
        "R9":  {"interior": 70, "corner": 100},
        "R10": {"interior": 70, "corner": 100},
    }
    if base in medium_high_density:
        if lot_type == "corner":
            return medium_high_density[base].get("corner", 80)
        return medium_high_density[base].get("interior", 65)

    return None  # No specific lot coverage limit
