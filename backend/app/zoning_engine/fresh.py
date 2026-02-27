"""
FRESH (Food Retail Expansion to Support Health) Program.

ZR 63-02 et seq.  Provides FAR bonus for full-line grocery stores in
designated FRESH-eligible areas (food deserts mapped by DCP/EDC).

Eligibility
-----------
- Site in a mapped FRESH zone (specific community districts)
- Food retail space of at least 6,000 SF ground floor
- Must be a full-line grocery store

Bonus
-----
- In R districts:  +0.5 FAR for food retail floor area
- In C/M districts: varies by underlying district
- Height bonus:  +5 ft in contextual districts
- Tax incentives: 25-year ICAP abatement in some CDs

Source: ZR 63-02, NYC EDC FRESH Program map
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.schemas import LotProfile


# ──────────────────────────────────────────────────────────────────
# FRESH-ELIGIBLE COMMUNITY DISTRICTS
# Borough-CD integer format (borough * 100 + cd_number)
# Source: NYC Dept of City Planning / EDC FRESH Zone map
# ──────────────────────────────────────────────────────────────────

FRESH_ELIGIBLE_CDS: set[int] = {
    # Bronx (borough 2)
    201, 202, 203, 204, 205, 206, 207, 209, 210, 211, 212,
    # Brooklyn (borough 3)
    301, 303, 304, 305, 308, 313, 316, 317,
    # Manhattan (borough 1)
    109, 110, 111, 112,
    # Queens (borough 4)
    401, 403, 412, 414,
    # Staten Island (borough 5)
    501,
}

FRESH_MIN_STORE_SF = 6_000   # Minimum grocery store floor area
FRESH_FAR_BONUS = 0.5        # Additional FAR for food retail space
FRESH_HEIGHT_BONUS_FT = 5    # Additional height in contextual districts


# ──────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────

def is_fresh_eligible(lot: LotProfile) -> bool:
    """Check if a lot is in a FRESH-eligible food desert area."""
    if not lot.pluto or not lot.pluto.cd:
        return False
    return lot.pluto.cd in FRESH_ELIGIBLE_CDS


def get_fresh_bonus(lot: LotProfile) -> dict | None:
    """Calculate FRESH program bonus if eligible.

    Returns dict with bonus details, or None if not eligible.
    """
    if not is_fresh_eligible(lot):
        return None

    lot_area = lot.lot_area or 0
    additional_zfa = round(FRESH_FAR_BONUS * lot_area)

    return {
        "far_bonus": FRESH_FAR_BONUS,
        "additional_zfa": additional_zfa,
        "height_bonus_ft": FRESH_HEIGHT_BONUS_FT,
        "min_store_sf": FRESH_MIN_STORE_SF,
        "eligible_cd": lot.pluto.cd,
        "description": (
            f"+{FRESH_FAR_BONUS} FAR bonus for food retail "
            f"(+{additional_zfa:,} ZFA). "
            f"Requires min {FRESH_MIN_STORE_SF:,} SF full-line grocery store."
        ),
    }
