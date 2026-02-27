"""
Large-Scale Residential Development (LSRD) and
Large-Scale General Development (LSGD) provisions.

LSRD (ZR 78-00)
----------------
Sites >= 1.5 acres (65,340 SF) in residential districts R3-R10.
CPC special permit allows planned development with:
  - Modified yard requirements
  - Modified height and setback
  - Modified tower coverage rules
  - Distribution of floor area across site
  - Required public amenities (open space, community facility)

LSGD (ZR 74-74)
----------------
Mixed-use sites >= 1.5 acres in R6-R10 or C1-C6 districts.
CPC special permit allows broader modifications:
  - Distribution of bulk across sub-lots
  - Mix of uses across the development
  - Modified parking requirements
  - Phased development approval
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.schemas import LotProfile


# ──────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────

LSRD_MIN_LOT_AREA_SF = 65_340  # 1.5 acres in square feet
LSGD_MIN_LOT_AREA_SF = 65_340  # 1.5 acres in square feet

# Base district groups (without contextual suffix) eligible for LSRD
_LSRD_ELIGIBLE_GROUPS = {"R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10"}

# Base district groups eligible for LSGD
_LSGD_ELIGIBLE_GROUPS = {
    "R6", "R7", "R8", "R9", "R10",
    "C1", "C2", "C4", "C5", "C6",
}

LSRD_MODIFICATIONS = [
    "Modified yard requirements",
    "Modified height and setback regulations",
    "Modified tower coverage rules",
    "Distribution of floor area across site",
    "Planned open space / public amenity requirement",
    "Modified lot coverage maximums",
]

LSGD_MODIFICATIONS = [
    "Distribution of bulk across sub-lots",
    "Mix of uses across the development",
    "Modified yard and setback requirements",
    "Modified parking requirements",
    "Phased development approval",
    "Modified lot coverage and open space",
]


# ──────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────

def _extract_base_group(district: str) -> str | None:
    """Extract the base district group from a full district string.

    Examples: 'R7A' -> 'R7', 'C6-4' -> 'C6', 'R10X' -> 'R10'
    """
    m = re.match(r"^(R\d+|C\d+|M\d+)", district)
    return m.group(1) if m else None


# ──────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────

def is_lsrd_eligible(lot: LotProfile) -> bool:
    """Check if lot qualifies for Large-Scale Residential Development."""
    lot_area = lot.lot_area or 0
    if lot_area < LSRD_MIN_LOT_AREA_SF:
        return False
    district = lot.zoning_districts[0] if lot.zoning_districts else ""
    base = _extract_base_group(district)
    return base in _LSRD_ELIGIBLE_GROUPS if base else False


def is_lsgd_eligible(lot: LotProfile) -> bool:
    """Check if lot qualifies for Large-Scale General Development."""
    lot_area = lot.lot_area or 0
    if lot_area < LSGD_MIN_LOT_AREA_SF:
        return False
    district = lot.zoning_districts[0] if lot.zoning_districts else ""
    base = _extract_base_group(district)
    return base in _LSGD_ELIGIBLE_GROUPS if base else False


def get_lsrd_details(lot: LotProfile) -> dict | None:
    """Get LSRD program details for an eligible lot."""
    if not is_lsrd_eligible(lot):
        return None
    return {
        "name": "Large-Scale Residential Development (LSRD)",
        "source_zr": "ZR 78-00",
        "min_lot_area_sf": LSRD_MIN_LOT_AREA_SF,
        "actual_lot_area_sf": lot.lot_area or 0,
        "available_modifications": LSRD_MODIFICATIONS,
        "process": "CPC Special Permit (discretionary)",
        "description": (
            f"Site qualifies for LSRD ({lot.lot_area or 0:,.0f} SF "
            f">= {LSRD_MIN_LOT_AREA_SF:,.0f} SF minimum). CPC special "
            "permit allows modification of bulk controls for planned "
            "residential development."
        ),
    }


def get_lsgd_details(lot: LotProfile) -> dict | None:
    """Get LSGD program details for an eligible lot."""
    if not is_lsgd_eligible(lot):
        return None
    return {
        "name": "Large-Scale General Development (LSGD)",
        "source_zr": "ZR 74-74",
        "min_lot_area_sf": LSGD_MIN_LOT_AREA_SF,
        "actual_lot_area_sf": lot.lot_area or 0,
        "available_modifications": LSGD_MODIFICATIONS,
        "process": "CPC Special Permit (discretionary)",
        "description": (
            f"Site qualifies for LSGD ({lot.lot_area or 0:,.0f} SF "
            f">= {LSGD_MIN_LOT_AREA_SF:,.0f} SF minimum). CPC special "
            "permit allows broad modifications for planned mixed-use "
            "development."
        ),
    }
