"""
Industrial Business Zone (IBZ) restrictions and
Industrial Incentive Area (IIA) provisions.

IBZ (NYC Executive Order 2006)
------------------------------
16 mapped industrial zones across NYC where certain conversions are
restricted to protect industrial jobs:
  - No residential conversion
  - No hotel development
  - No self-storage / mini-storage
  - Manufacturing and industrial uses protected

IIA (ULURP 2022)
-----------------
Tax incentives and zoning flexibility for industrial development
in designated IBZ areas:
  - Industrial & Commercial Abatement Program (ICAP) tax benefits
  - Relocation & Employment Assistance Program (REAP)
  - Enhanced energy cost savings
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.schemas import LotProfile


# ──────────────────────────────────────────────────────────────────
# IBZ COMMUNITY DISTRICTS
# Borough-CD integer format (borough * 100 + cd_number)
# Source: NYC SBS Industrial Business Zone map
# ──────────────────────────────────────────────────────────────────

IBZ_COMMUNITY_DISTRICTS: set[int] = {
    # Bronx
    201, 202, 206, 209,
    # Brooklyn
    301, 306, 307, 315, 317,
    # Queens
    401, 402, 405, 407, 412, 414,
    # Staten Island
    501, 502, 503,
}

IBZ_USE_RESTRICTIONS = [
    "No residential development or conversion",
    "No hotel development",
    "No self-storage or mini-storage facilities",
    "Manufacturing and industrial uses protected",
]

IIA_INCENTIVES = [
    "Industrial & Commercial Abatement Program (ICAP) tax benefits",
    "Relocation & Employment Assistance Program (REAP)",
    "Enhanced energy cost savings for qualifying facilities",
    "Expedited permitting for industrial construction",
]

# IIA is available in M-districts within IBZ areas
_IIA_ELIGIBLE_PREFIXES = ("M1", "M2", "M3")


# ──────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────

def is_ibz(lot: LotProfile) -> bool:
    """Check if lot is in an Industrial Business Zone.

    Requires both an M-district zoning AND a community district
    that is designated as an IBZ.
    """
    if not lot.pluto or not lot.pluto.cd:
        return False
    district = lot.zoning_districts[0] if lot.zoning_districts else ""
    if not district.startswith("M"):
        return False
    return lot.pluto.cd in IBZ_COMMUNITY_DISTRICTS


def get_ibz_restrictions(lot: LotProfile) -> dict | None:
    """Get IBZ restrictions for a lot, if applicable."""
    if not is_ibz(lot):
        return None
    return {
        "name": "Industrial Business Zone (IBZ)",
        "restrictions": IBZ_USE_RESTRICTIONS,
        "use_restriction": "no_residential",
        "source_zr": "NYC Executive Order (2006)",
        "description": (
            "Industrial Business Zone: residential, hotel, and "
            "self-storage conversions are restricted. "
            "Manufacturing and industrial uses protected."
        ),
    }


def is_iia_eligible(lot: LotProfile) -> bool:
    """Check if lot is eligible for Industrial Incentive Area benefits.

    Must be in an IBZ and zoned for manufacturing (M1-M3).
    """
    if not is_ibz(lot):
        return False
    district = lot.zoning_districts[0] if lot.zoning_districts else ""
    return any(district.startswith(p) for p in _IIA_ELIGIBLE_PREFIXES)


def get_iia_incentives(lot: LotProfile) -> dict | None:
    """Get IIA incentive details for an eligible lot."""
    if not is_iia_eligible(lot):
        return None
    return {
        "name": "Industrial Incentive Area (IIA)",
        "incentives": IIA_INCENTIVES,
        "source_zr": "NYC IIA Designation (ULURP 2022)",
        "description": (
            "Site in Industrial Incentive Area. Tax benefits and "
            "expedited permitting available for qualifying "
            "industrial development."
        ),
    }
