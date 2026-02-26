"""
NYC Zoning Resolution dormer rules for contextual districts (ZR 23-621).

In contextual (Quality Housing) districts, a building may have a dormer
that rises above the maximum base height without requiring the full
setback. This effectively adds floor area to upper stories.

The dormer provision allows a portion of the street-facing wall to
continue rising straight up past the base height to the max building
height, while the rest of the facade must set back.

Key rule: The dormer width may not exceed 60% of the street wall width.

Effect on development:
  Without dormer: floors above base_height_max must be fully set back
  With dormer: 60% of frontage rises straight up, only 40% sets back
  This adds ~10-15% more area to upper floors.
"""

from __future__ import annotations


# Districts where dormer rules apply (all contextual/QH districts)
DORMER_ELIGIBLE_DISTRICTS = {
    "R5A", "R5B", "R5D",
    "R6A", "R6B",
    "R7A", "R7B", "R7D", "R7X",
    "R8A", "R8B", "R8X",
    "R9A", "R9X", "R9D",
    "R10A", "R10X",
}

# Dormer parameters
MAX_DORMER_WIDTH_PCT = 0.60  # 60% of street wall width


def get_dormer_rules(district: str) -> dict:
    """Get dormer rules for a district.

    Returns dict with:
        eligible: whether dormers are allowed
        max_width_pct: maximum dormer width as % of street wall
        upper_floor_area_factor: multiplier for upper floor footprint
            (accounts for the dormer + setback combination)
    """
    district = district.strip().upper()

    if district not in DORMER_ELIGIBLE_DISTRICTS:
        return {
            "eligible": False,
            "max_width_pct": 0,
            "upper_floor_area_factor": 1.0,  # No dormer, full setback
        }

    # With dormer: 60% of frontage continues up, 40% sets back
    # Upper floor area = (0.60 * full_depth) + (0.40 * (full_depth - setback))
    # Simplified: the upper floor retains more area than a full setback
    # For a 10 ft setback on a 100 ft deep lot:
    #   Without dormer: upper = (frontage - setback) * depth = less area
    #   With dormer: upper = 0.60 * frontage * depth + 0.40 * (frontage - setback) * depth
    # The factor depends on the setback-to-depth ratio

    return {
        "eligible": True,
        "max_width_pct": MAX_DORMER_WIDTH_PCT,
        "upper_floor_area_factor": 0.92,  # Typical: retains ~92% of base floor area
        # (vs ~85% without dormer, assuming 10-15 ft setback on 100 ft depth)
    }


def calculate_upper_floor_area(
    base_footprint: float,
    lot_frontage: float,
    lot_depth: float,
    setback: float,
    district: str,
) -> float:
    """Calculate upper floor area (above base height) accounting for dormers.

    In QH districts with dormers:
      - 60% of the street frontage continues straight up (dormer portion)
      - 40% of the street frontage sets back by the required amount
      - The rest of the floor (sides, rear) is unchanged

    Args:
        base_footprint: Ground/base floor area in SF
        lot_frontage: Lot frontage width in ft
        lot_depth: Lot depth in ft
        setback: Required setback above base in ft
        district: Zoning district

    Returns:
        Upper floor area in SF
    """
    rules = get_dormer_rules(district)

    if not rules["eligible"] or setback <= 0:
        # Non-contextual or no setback: upper floor = base minus full setback
        effective_depth = max(0, lot_depth - setback) if setback > 0 else lot_depth
        return lot_frontage * effective_depth

    # With dormer:
    # Dormer portion (60% of frontage): no setback, full depth
    dormer_width = lot_frontage * MAX_DORMER_WIDTH_PCT
    dormer_area = dormer_width * lot_depth

    # Setback portion (40% of frontage): reduced by setback
    setback_width = lot_frontage * (1 - MAX_DORMER_WIDTH_PCT)
    setback_depth = max(0, lot_depth - setback)
    setback_area = setback_width * setback_depth

    upper_area = dormer_area + setback_area

    # Can't exceed base footprint (in case of complex lot shapes)
    return min(upper_area, base_footprint)
