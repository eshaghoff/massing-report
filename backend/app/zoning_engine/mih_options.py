"""
NYC Mandatory Inclusionary Housing (MIH) program options.

MIH (ZR 23-154, 23-90) applies in areas that have been rezoned with MIH
designation. Developers in MIH areas MUST provide affordable housing
to access the bonus FAR — there is no "as-of-right" option without
affordability in MIH areas.

Three MIH options (developer chooses one):

Option 1:  25% of residential floor area at an average of 60% AMI
           (units can range 40%-80% AMI)

Option 2:  30% of residential floor area at an average of 80% AMI
           (units can range 60%-115% AMI)

Deep Affordability Option:
           20% of residential floor area at an average of 40% AMI
           (units can range 20%-60% AMI)

Workforce Option (in certain areas):
           30% of residential floor area at an average of 115% AMI

In some mapped areas, the City Council may designate which options apply.

AMI = Area Median Income for the NYC metropolitan area.
As of 2024, NYC AMI for a family of 3 is approximately $106,700.
"""

from __future__ import annotations

from app.zoning_engine.far_tables import MIH_BONUS, RESIDENTIAL_FAR, COMMERCIAL_RESIDENTIAL_EQUIVALENTS


# ──────────────────────────────────────────────────────────────────
# MIH OPTION DEFINITIONS
# ──────────────────────────────────────────────────────────────────

MIH_OPTIONS = {
    "option_1": {
        "name": "MIH Option 1",
        "affordable_pct": 0.25,       # 25% of residential floor area
        "avg_ami": 60,                 # Average 60% AMI
        "ami_range": (40, 80),         # Range of AMI levels
        "description": "25% of residential floor area affordable at avg 60% AMI",
    },
    "option_2": {
        "name": "MIH Option 2",
        "affordable_pct": 0.30,        # 30% of residential floor area
        "avg_ami": 80,                 # Average 80% AMI
        "ami_range": (60, 115),
        "description": "30% of residential floor area affordable at avg 80% AMI",
    },
    "deep_affordability": {
        "name": "Deep Affordability",
        "affordable_pct": 0.20,        # 20% of residential floor area
        "avg_ami": 40,                 # Average 40% AMI
        "ami_range": (20, 60),
        "description": "20% of residential floor area affordable at avg 40% AMI",
    },
    "workforce": {
        "name": "Workforce Option",
        "affordable_pct": 0.30,        # 30% of residential floor area
        "avg_ami": 115,                # Average 115% AMI
        "ami_range": (90, 135),
        "description": "30% of residential floor area affordable at avg 115% AMI",
    },
}

# ──────────────────────────────────────────────────────────────────
# AMI RENT SCHEDULES (approximate monthly rents by AMI level, 2024)
# These are HUD-published rent limits for NYC MSA.
# ──────────────────────────────────────────────────────────────────

AMI_RENTS_2024 = {
    # AMI %: {unit_type: monthly_rent}
    30: {"studio": 567, "1br": 607, "2br": 729, "3br": 842},
    40: {"studio": 756, "1br": 810, "2br": 972, "3br": 1123},
    50: {"studio": 945, "1br": 1012, "2br": 1215, "3br": 1404},
    60: {"studio": 1134, "1br": 1215, "2br": 1458, "3br": 1685},
    80: {"studio": 1512, "1br": 1620, "2br": 1944, "3br": 2246},
    100: {"studio": 1890, "1br": 2025, "2br": 2430, "3br": 2808},
    115: {"studio": 2174, "1br": 2329, "2br": 2795, "3br": 3229},
    130: {"studio": 2457, "1br": 2633, "2br": 3159, "3br": 3650},
}


def get_mih_bonus_far(district: str) -> float | None:
    """Get the additional FAR available through MIH bonus.

    Returns the difference between MIH max FAR and base QH FAR,
    or None if MIH doesn't apply to this district.
    """
    district = district.strip().upper()

    # Check direct match
    entry = MIH_BONUS.get(district)
    if entry:
        return round(entry["mih_max"] - entry["base_qh"], 2)

    # Check commercial district equivalent
    equiv = COMMERCIAL_RESIDENTIAL_EQUIVALENTS.get(district)
    if equiv:
        entry = MIH_BONUS.get(equiv)
        if entry:
            return round(entry["mih_max"] - entry["base_qh"], 2)

    return None


def get_mih_max_far(district: str) -> float | None:
    """Get the maximum residential FAR achievable with MIH bonus."""
    district = district.strip().upper()

    entry = MIH_BONUS.get(district)
    if entry:
        return entry["mih_max"]

    equiv = COMMERCIAL_RESIDENTIAL_EQUIVALENTS.get(district)
    if equiv:
        entry = MIH_BONUS.get(equiv)
        if entry:
            return entry["mih_max"]

    return None


def calculate_mih_program(
    mih_option: str,
    total_residential_sf: float,
    unit_mix: dict | None = None,
) -> dict:
    """Calculate MIH affordable housing requirements for a given option.

    Args:
        mih_option: One of "option_1", "option_2", "deep_affordability", "workforce"
        total_residential_sf: Total residential floor area in SF
        unit_mix: Optional dict of {unit_type: count} for rent calculation

    Returns dict with:
        option_name, affordable_pct, affordable_sf, market_rate_sf,
        avg_ami, ami_range, estimated_affordable_units, rent_schedule
    """
    option = MIH_OPTIONS.get(mih_option, MIH_OPTIONS["option_1"])

    affordable_sf = total_residential_sf * option["affordable_pct"]
    market_rate_sf = total_residential_sf - affordable_sf

    # Estimate affordable units (assume avg ~700 SF per affordable unit)
    avg_affordable_unit_sf = 650
    estimated_affordable_units = max(1, int(affordable_sf / avg_affordable_unit_sf))

    # Rent schedule at the option's average AMI
    avg_ami = option["avg_ami"]
    rents = AMI_RENTS_2024.get(avg_ami, {})

    # Calculate revenue impact
    market_rents = AMI_RENTS_2024.get(100, {})
    if rents and market_rents:
        # Weighted average rent difference per unit per month
        avg_affordable_rent = sum(rents.values()) / len(rents)
        avg_market_rent = sum(market_rents.values()) / len(market_rents)
        monthly_rent_gap = avg_market_rent - avg_affordable_rent
        annual_revenue_impact = monthly_rent_gap * estimated_affordable_units * 12
    else:
        annual_revenue_impact = 0

    return {
        "option_key": mih_option,
        "option_name": option["name"],
        "description": option["description"],
        "affordable_pct": option["affordable_pct"],
        "affordable_sf": round(affordable_sf),
        "market_rate_sf": round(market_rate_sf),
        "avg_ami": avg_ami,
        "ami_range": option["ami_range"],
        "estimated_affordable_units": estimated_affordable_units,
        "rent_schedule": rents,
        "estimated_annual_revenue_impact": round(annual_revenue_impact),
    }


def get_all_mih_options(
    total_residential_sf: float,
) -> list[dict]:
    """Calculate all MIH options for comparison.

    Returns a list of program details for each MIH option.
    """
    results = []
    for option_key in ["option_1", "option_2", "deep_affordability", "workforce"]:
        program = calculate_mih_program(option_key, total_residential_sf)
        results.append(program)
    return results
