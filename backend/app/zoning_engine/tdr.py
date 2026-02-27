"""
Transfer of Development Rights (TDR) mechanisms.

NYC allows unused development rights to be transferred between lots
through several mechanisms:

1. Landmark TDR (ZR 74-79, expanded by City of Yes Dec 2024)
   - From designated NYC landmarks to receiving lots
   - Chair certification (no ULURP), non-adjacent OK, 20% cap

2. East Midtown TDR Bank (ZR 81-64)
   - Landmark preservation + public realm improvement TDR
   - Max 27.0 FAR with TDR

3. West Chelsea / High Line TDR (ZR 98-04)
   - Transfer from High Line improvement donor sites
   - Base 5.0 -> max 7.5 FAR

4. Hudson Yards TDR (ZR 93-32)
   - Eastern Rail Yard development rights
   - District improvement bonus
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.schemas import LotProfile


# ──────────────────────────────────────────────────────────────────
# LANDMARK TDR (City of Yes expansion, effective Dec 5, 2024)
# ZR 74-79 as amended
# ──────────────────────────────────────────────────────────────────

LANDMARK_TDR = {
    "max_far_increase_pct": 0.20,       # 20% of receiving lot's permitted FAR
    "chair_certification": True,         # CPC chair cert, no full ULURP
    "adjacency_required": False,         # Non-adjacent transfers OK (City of Yes)
    "contribution_to_preservation": True, # Required preservation fund payment
    "source_zr": "ZR 74-79",
}

# Districts eligible to RECEIVE landmark TDR
LANDMARK_TDR_ELIGIBLE_DISTRICTS: set[str] = {
    # R6+
    "R6", "R6A", "R6B", "R7-1", "R7-2", "R7A", "R7B", "R7D", "R7X",
    "R8", "R8A", "R8B", "R8X", "R9", "R9A", "R9X", "R9D",
    "R10", "R10A", "R10X", "R11", "R12",
    # C4+
    "C4-4", "C4-4A", "C4-5", "C4-5A", "C4-5D", "C4-5X",
    "C4-6", "C4-6A", "C4-7",
    # C5
    "C5-1", "C5-2", "C5-2.5", "C5-3", "C5-5",
    # C6
    "C6-1", "C6-1A", "C6-2", "C6-2A", "C6-2M", "C6-3", "C6-3A",
    "C6-3D", "C6-3X", "C6-4", "C6-4A", "C6-4M", "C6-4X",
    "C6-5", "C6-5.5", "C6-6", "C6-6.5", "C6-7", "C6-7T", "C6-9",
    # C1/C2 with high-density residential
    "C1-6", "C1-6A", "C1-7", "C1-7A", "C1-8", "C1-8A", "C1-8X", "C1-9", "C1-9A",
    "C2-6", "C2-6A", "C2-7", "C2-7A", "C2-7X", "C2-8", "C2-8A",
}


# ──────────────────────────────────────────────────────────────────
# SPECIAL DISTRICT TDR BANKS
# ──────────────────────────────────────────────────────────────────

EAST_MIDTOWN_TDR = {
    "name": "East Midtown TDR Bank",
    "district_code": "EM",
    "base_far": 15.0,
    "max_far_with_tdr": 27.0,
    "public_realm_contribution_per_sf": 61.49,  # $/SF of transferred FAR
    "landmark_preservation_fund": True,
    "source_zr": "ZR 81-64",
    "description": (
        "East Midtown landmark preservation TDR. Transfer development "
        "rights from designated landmarks with public realm improvement "
        "contribution."
    ),
}

WEST_CHELSEA_TDR = {
    "name": "West Chelsea / High Line TDR",
    "district_code": "WCh",
    "base_far": 5.0,
    "max_far_with_tdr": 7.5,
    "transfer_mechanism": "Chair certification (as-of-right)",
    "source_zr": "ZR 98-04",
    "description": (
        "High Line improvement area TDR. Unused development rights "
        "from donor sites along the High Line corridor."
    ),
}

HUDSON_YARDS_TDR = {
    "name": "Hudson Yards Development Rights",
    "district_code": "HY",
    "base_far": 10.0,
    "max_additional_far": 10.0,
    "district_improvement_bonus": True,
    "source_zr": "ZR 93-32",
    "description": (
        "Hudson Yards district improvement bonus. Additional FAR "
        "from Eastern Rail Yard development rights."
    ),
}


# ──────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────

def is_landmark_tdr_eligible(lot: LotProfile) -> bool:
    """Check if a lot can receive landmark TDR based on its zoning district."""
    district = lot.zoning_districts[0] if lot.zoning_districts else ""
    return district in LANDMARK_TDR_ELIGIBLE_DISTRICTS


def get_landmark_tdr_bonus(lot: LotProfile, base_far: float) -> dict | None:
    """Calculate potential landmark TDR bonus.

    Args:
        lot: LotProfile
        base_far: The lot's base permitted FAR (residential or commercial max)

    Returns:
        Dict with TDR bonus details, or None if not eligible.
    """
    if not is_landmark_tdr_eligible(lot):
        return None

    additional_far = round(base_far * LANDMARK_TDR["max_far_increase_pct"], 2)
    lot_area = lot.lot_area or 0

    return {
        "far_bonus": additional_far,
        "additional_zfa": round(additional_far * lot_area),
        "mechanism": "Chair certification (no ULURP)",
        "adjacency_required": False,
        "preservation_contribution_required": True,
        "source_zr": LANDMARK_TDR["source_zr"],
        "description": (
            f"+{additional_far:.2f} FAR via landmark TDR "
            f"(20% of base {base_far:.2f} FAR). "
            f"Chair certification, non-adjacent transfers permitted."
        ),
    }


def check_special_district_tdr(lot: LotProfile) -> dict | None:
    """Check if lot is in a special district with a TDR bank.

    Returns TDR bank details or None.
    """
    spdist_codes = lot.special_districts or []
    lot_area = lot.lot_area or 0

    for code in spdist_codes:
        code = code.strip()

        if code == "EM":
            additional = EAST_MIDTOWN_TDR["max_far_with_tdr"] - EAST_MIDTOWN_TDR["base_far"]
            return {
                "type": "east_midtown_tdr",
                "name": EAST_MIDTOWN_TDR["name"],
                "base_far": EAST_MIDTOWN_TDR["base_far"],
                "max_far_with_tdr": EAST_MIDTOWN_TDR["max_far_with_tdr"],
                "far_bonus": additional,
                "additional_zfa": round(additional * lot_area),
                "public_realm_contribution": round(
                    EAST_MIDTOWN_TDR["public_realm_contribution_per_sf"]
                    * additional * lot_area
                ),
                "source_zr": EAST_MIDTOWN_TDR["source_zr"],
                "description": EAST_MIDTOWN_TDR["description"],
            }

        if code == "WCh":
            additional = WEST_CHELSEA_TDR["max_far_with_tdr"] - WEST_CHELSEA_TDR["base_far"]
            return {
                "type": "west_chelsea_tdr",
                "name": WEST_CHELSEA_TDR["name"],
                "base_far": WEST_CHELSEA_TDR["base_far"],
                "max_far_with_tdr": WEST_CHELSEA_TDR["max_far_with_tdr"],
                "far_bonus": additional,
                "additional_zfa": round(additional * lot_area),
                "source_zr": WEST_CHELSEA_TDR["source_zr"],
                "description": WEST_CHELSEA_TDR["description"],
            }

        if code == "HY":
            return {
                "type": "hudson_yards_tdr",
                "name": HUDSON_YARDS_TDR["name"],
                "base_far": HUDSON_YARDS_TDR["base_far"],
                "far_bonus": HUDSON_YARDS_TDR["max_additional_far"],
                "additional_zfa": round(
                    HUDSON_YARDS_TDR["max_additional_far"] * lot_area
                ),
                "source_zr": HUDSON_YARDS_TDR["source_zr"],
                "description": HUDSON_YARDS_TDR["description"],
            }

    return None
