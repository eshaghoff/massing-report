"""
NYC Zoning Resolution Use Group permissions.

Use Groups 1-18 categorize permitted uses across zoning districts.
"""

from __future__ import annotations

# Use Group descriptions
USE_GROUP_NAMES = {
    1: "Residences (1-2 family)",
    2: "Residences (all types)",
    3: "Community Facilities (schools, libraries, museums)",
    4: "Community Facilities (houses of worship, hospitals)",
    5: "Hotels, transient accommodations",
    6: "Retail (general), eating/drinking, offices",
    7: "Home furnishings, large retail",
    8: "Amusement, recreation (indoor)",
    9: "Retail (general), service establishments",
    10: "Retail (larger), home maintenance services",
    11: "Custom manufacturing, retail (specialized)",
    12: "General service, amusement (outdoor), auto",
    13: "Automotive, boating, open amusements",
    14: "Amusements, boating (large-scale)",
    15: "Light manufacturing",
    16: "Heavy commercial, some manufacturing",
    17: "Manufacturing (general)",
    18: "Heavy manufacturing",
}

# Districts and their permitted Use Groups (as-of-right)
DISTRICT_USE_GROUPS = {
    # Residential
    "R1":   [1, 3, 4],
    "R2":   [1, 3, 4],
    "R3":   [1, 2, 3, 4],
    "R4":   [1, 2, 3, 4],
    "R5":   [1, 2, 3, 4],
    "R6":   [1, 2, 3, 4],
    "R7":   [1, 2, 3, 4],
    "R8":   [1, 2, 3, 4],
    "R9":   [1, 2, 3, 4],
    "R10":  [1, 2, 3, 4],

    # Commercial
    "C1":   [1, 2, 3, 4, 5, 6],
    "C2":   [1, 2, 3, 4, 5, 6, 9],
    "C3":   [1, 2, 3, 4, 6, 9, 12],
    "C4":   [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "C5":   [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    "C6":   [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "C7":   [8, 14],
    "C8":   [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16],

    # Manufacturing
    "M1":   [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17],
    "M2":   [15, 16, 17],
    "M3":   [15, 16, 17, 18],
}


def get_permitted_uses(district: str) -> dict:
    """Get permitted uses for a zoning district.

    Returns dict with:
        use_groups: list of permitted UG numbers
        ground_floor_commercial: whether ground-floor commercial is required/allowed
        manufacturing_allowed: bool
        community_facility_allowed: bool
        residential_allowed: bool
    """
    district = district.strip().upper()
    base = _get_base_district(district)

    use_groups = DISTRICT_USE_GROUPS.get(base, [])

    return {
        "use_groups": use_groups,
        "use_group_names": {ug: USE_GROUP_NAMES.get(ug, "") for ug in use_groups},
        "residential_allowed": any(ug in (1, 2) for ug in use_groups),
        "community_facility_allowed": any(ug in (3, 4) for ug in use_groups),
        "commercial_allowed": any(ug in (5, 6, 7, 8, 9, 10, 11) for ug in use_groups),
        "manufacturing_allowed": any(ug in (15, 16, 17, 18) for ug in use_groups),
        "ground_floor_commercial_required": _ground_floor_commercial_required(district),
        "ground_floor_commercial_permitted": _ground_floor_commercial_permitted(district),
    }


def _get_base_district(district: str) -> str:
    import re
    match = re.match(r'^(R\d+|C\d+|M\d+)', district)
    if match:
        return match.group(1)
    return district


def _ground_floor_commercial_required(district: str) -> bool:
    """Some commercial districts require ground floor retail."""
    # C4-5X and similar mandate active ground-floor uses
    return district in ("C4-5X", "C4-5D", "C6-3A", "C6-3X")


def _ground_floor_commercial_permitted(district: str) -> bool:
    """Check if ground-floor commercial is permitted."""
    base = _get_base_district(district)
    return base.startswith("C") or base.startswith("M1")
