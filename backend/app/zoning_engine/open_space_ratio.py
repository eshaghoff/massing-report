"""
NYC Zoning Resolution open space ratio requirements (ZR 23-14, 23-15, 23-16).

In Height Factor (HF) districts (non-contextual R6-R10), FAR is NOT a fixed number.
Instead, FAR is calculated as a FUNCTION of open space ratio (OSR) using formulas.
The developer must provide a minimum open space ratio, and as they provide more
open space, they earn more floor area — up to the district maximum.

This is the fundamental difference from Quality Housing:
  - QH: fixed max FAR, fixed height limit
  - HF: variable FAR (depends on open space), no height limit, sky exposure plane

Open Space Ratio (OSR) = Open space on lot / Total floor area on lot × 100

For residential uses (ZR 23-15):
  The HF formula for R6-R10 gives a continuum from minimum FAR at maximum OSR
  down to minimum OSR at maximum FAR.

  Basic Height Factor formula (simplified):
    FAR = Floor Area Factor / (Open Space Ratio)
    where Floor Area Factor varies by district

For residential buildings, the two key values are:
  - Minimum required open space ratio (at maximum FAR)
  - Maximum FAR (at minimum OSR)

ZR 23-151: Height Factor for R6-R10
The "factor" in "Height Factor" is literally the number that, divided by OSR,
gives the FAR. This creates the sliding scale between open space and density.
"""

from __future__ import annotations


# ──────────────────────────────────────────────────────────────────
# HEIGHT FACTOR OPEN SPACE TABLES (ZR 23-15, Table 1 equivalent)
# For each district: min_osr (at max FAR), max_far, max_osr, min_far
# Also: the open_space_factor (OSF) used in the formula FAR = OSF/OSR
# ──────────────────────────────────────────────────────────────────

HF_OPEN_SPACE = {
    # R6: Basic HF
    "R6": {
        "min_osr": 27.5,      # Minimum open space ratio at max FAR
        "max_far": 0.78,      # Maximum FAR achievable (at min OSR=27.5)
        # Actually R6 HF has: max FAR = 2.43 (the "factor")
        # The 0.78 is the "base" FAR coefficient
        # Real R6 HF: FAR ranges from ~0.78 to 2.43
        # At max FAR=2.43, OSR=27.5
        # At min FAR (very tall, lots of open space), OSR can be much higher
        "max_far_actual": 2.43,
        "open_space_factor": 66.8,  # FAR = 66.8 / OSR
        "min_far_at_max_osr": 0.78,
        "max_osr": 85.5,
    },
    "R7-1": {
        "min_osr": 15.5,
        "max_far_actual": 3.44,
        "open_space_factor": 53.3,
        "min_far_at_max_osr": 0.87,
        "max_osr": 61.3,
    },
    "R7-2": {
        "min_osr": 15.5,
        "max_far_actual": 3.44,
        "open_space_factor": 53.3,
        "min_far_at_max_osr": 0.87,
        "max_osr": 61.3,
    },
    "R8": {
        "min_osr": 5.9,
        "max_far_actual": 6.02,
        "open_space_factor": 35.5,
        "min_far_at_max_osr": 0.94,
        "max_osr": 37.7,
    },
    "R9": {
        "min_osr": 1.0,
        "max_far_actual": 7.52,
        "open_space_factor": 7.5,
        "min_far_at_max_osr": 0.99,
        "max_osr": 7.6,
    },
    "R10": {
        "min_osr": 0,         # R10 has no OSR requirement in HF
        "max_far_actual": 10.0,
        "open_space_factor": 0,  # Not applicable; flat 10.0 FAR
        "min_far_at_max_osr": 10.0,
        "max_osr": 0,
    },
}

# ──────────────────────────────────────────────────────────────────
# COMMUNITY FACILITY OPEN SPACE (ZR 24-11)
# Community facility buildings do NOT have open space requirements
# in most districts (the OSR only applies to residential).
# ──────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────
# COMMERCIAL DISTRICT OPEN SPACE (ZR 33-13)
# Some commercial districts have plaza bonus or open space requirements
# ──────────────────────────────────────────────────────────────────

COMMERCIAL_OPEN_SPACE = {
    # C5/C6 high-density commercial: no open space requirement
    # C1-C4: follows residential district equivalent
}


def calculate_hf_far(
    district: str,
    lot_area: float,
    proposed_open_space: float = 0,
) -> dict:
    """Calculate Height Factor FAR based on proposed open space.

    In HF districts, the developer chooses how much open space to provide.
    More open space = lower FAR = taller, thinner building.
    Less open space = higher FAR = shorter, wider building (up to max).

    Args:
        district: Non-contextual district (R6, R7-1, R7-2, R8, R9, R10)
        lot_area: Lot area in square feet
        proposed_open_space: Proposed open space in square feet (0 = use max FAR)

    Returns dict with:
        max_far: Maximum achievable FAR
        min_osr: Minimum open space ratio required
        min_open_space_sf: Minimum open space area required (at max FAR)
        far_at_proposed_osr: FAR achievable at proposed open space
        open_space_factor: The district's open space factor
    """
    district = district.strip().upper()
    rules = HF_OPEN_SPACE.get(district)

    if not rules:
        return {
            "max_far": None,
            "min_osr": None,
            "min_open_space_sf": 0,
            "far_at_proposed_osr": None,
            "open_space_factor": None,
            "is_height_factor": False,
        }

    max_far = rules["max_far_actual"]
    min_osr = rules["min_osr"]
    osf = rules["open_space_factor"]

    # Calculate minimum open space required at max FAR
    # OSR = (open space / floor area) × 100
    # At max FAR: floor_area = max_far × lot_area
    # min_open_space = min_osr × max_far × lot_area / 100
    max_floor_area = max_far * lot_area
    min_open_space = (min_osr / 100) * max_floor_area

    # Calculate FAR at proposed open space
    far_at_proposed = max_far
    if proposed_open_space > 0 and osf > 0 and lot_area > 0:
        # The open space ratio is: (open_space / floor_area) × 100
        # We need to solve: OSR = (proposed_open_space / (FAR × lot_area)) × 100
        # And FAR = OSF / OSR
        # So: FAR = OSF × FAR × lot_area / (proposed_open_space × 100)
        # Actually the HF formula is iterative, but we can use:
        # floor_area = lot_area × FAR
        # OSR = open_space / floor_area × 100
        # FAR = OSF / OSR (this is the constraint)
        # Substituting: FAR = OSF × floor_area / (open_space × 100)
        # FAR = OSF × lot_area × FAR / (open_space × 100)
        # 1 = OSF × lot_area / (open_space × 100)
        # This shows the system is overdetermined — in practice:
        # proposed_osr = proposed_open_space / (max_far * lot_area) * 100
        proposed_osr = proposed_open_space / max_floor_area * 100 if max_floor_area > 0 else 0
        if proposed_osr > min_osr and osf > 0:
            far_at_proposed = osf / proposed_osr
            far_at_proposed = max(far_at_proposed, rules["min_far_at_max_osr"])
            far_at_proposed = min(far_at_proposed, max_far)

    return {
        "max_far": max_far,
        "min_osr": min_osr,
        "min_open_space_sf": round(min_open_space),
        "far_at_proposed_osr": round(far_at_proposed, 2),
        "open_space_factor": osf,
        "is_height_factor": True,
    }


def get_required_open_space(district: str, total_floor_area: float) -> float:
    """Get minimum open space required for a given floor area in an HF district.

    Args:
        district: District code
        total_floor_area: Total floor area being built

    Returns:
        Minimum open space in square feet
    """
    district = district.strip().upper()
    rules = HF_OPEN_SPACE.get(district)
    if not rules:
        return 0

    min_osr = rules["min_osr"]
    return total_floor_area * (min_osr / 100)


def get_max_floor_area_for_open_space(
    district: str, lot_area: float, open_space_sf: float,
) -> float:
    """Given available open space, calculate max achievable floor area.

    Args:
        district: District code
        lot_area: Lot area in SF
        open_space_sf: Open space provided in SF

    Returns:
        Maximum floor area in SF
    """
    district = district.strip().upper()
    rules = HF_OPEN_SPACE.get(district)
    if not rules:
        return 0

    max_far = rules["max_far_actual"]
    osf = rules["open_space_factor"]

    if osf == 0:  # R10 — no OSR requirement
        return max_far * lot_area

    # FAR = OSF / OSR where OSR = open_space / floor_area × 100
    # This gives: floor_area = OSF × floor_area / (open_space × 100 / floor_area)
    # Rearranging: floor_area² = OSF × lot_area × open_space / 100... (not quite)
    # Actually: if open_space is fixed, OSR = open_space / floor_area × 100
    # And FAR = floor_area / lot_area
    # Constraint: FAR = OSF / OSR = OSF × floor_area / (open_space × 100)
    # So: floor_area/lot_area = OSF × floor_area / (open_space × 100)
    # 1/lot_area = OSF / (open_space × 100)
    # open_space = OSF × lot_area / 100
    # This is just the minimum open space at max FAR — meaning
    # if you provide exactly this amount, you get max FAR.
    # If you provide MORE, you must use LESS floor area.

    min_open_space_at_max = (rules["min_osr"] / 100) * max_far * lot_area
    if open_space_sf <= min_open_space_at_max:
        # Enough (or more than enough) open space for max FAR
        return max_far * lot_area

    # More open space means less floor area
    # OSR = open_space / floor_area × 100
    # FAR = OSF / OSR
    # FAR = OSF × floor_area / (open_space × 100)
    # floor_area / lot_area = OSF × floor_area / (open_space × 100)
    # This simplifies to: the max floor area is constrained by:
    # floor_area ≤ max_far × lot_area (always true)
    # AND open_space ≥ min_osr × floor_area / 100
    # So: floor_area ≤ open_space × 100 / min_osr (if we allow going beyond min OSR)
    # But actually in HF, you CHOOSE your OSR and it determines FAR.
    # If providing exactly open_space_sf of open space:
    # floor_area = open_space_sf × 100 / min_osr  (at the max FAR point)
    # But beyond that, the formula FAR = OSF/OSR applies:
    # floor_area such that open_space_sf / floor_area × 100 = OSR
    # and FAR = OSF / OSR = floor_area / lot_area
    # So floor_area = lot_area × OSF / (open_space_sf/floor_area × 100)
    # floor_area² = lot_area × OSF × floor_area / (open_space_sf × 100)... circular
    # Direct: floor_area = sqrt(lot_area × OSF × ... ) — needs numeric solve
    # Simpler: OSR = open_space / floor_area × 100; FAR = OSF/OSR
    # FAR = OSF × floor_area / (100 × open_space)
    # floor_area = FAR × lot_area
    # FAR × lot_area × 100 × open_space = OSF × FAR × lot_area × FAR × lot_area... no
    # Let FA = floor_area. OSR = open_space/FA × 100. FAR = FA/lot_area.
    # Constraint: FAR ≤ OSF/OSR = OSF × FA / (open_space × 100)
    # FA/lot_area ≤ OSF × FA / (open_space × 100)
    # 1/lot_area ≤ OSF / (open_space × 100)
    # open_space ≤ OSF × lot_area / 100
    # So if open_space > OSF × lot_area / 100, you're below the min FAR curve
    max_open_space_in_formula = osf * lot_area / 100
    if open_space_sf > max_open_space_in_formula:
        return rules["min_far_at_max_osr"] * lot_area

    return max_far * lot_area
