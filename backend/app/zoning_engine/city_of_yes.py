"""
City of Yes for Housing Opportunity provisions.

Adopted by NYC City Council on December 5, 2024 (ULURP N 240187 ZRY).
Effective date: December 5, 2024. Vesting deadline: December 5, 2025.

Key programs:
  1. Universal Affordability Preference (UAP) — 20% FAR bonus for affordable
     housing at avg ≤60% AMI, available citywide in R6-R12 districts.
  2. Transit-Oriented Development (TOD) — New contextual districts (R6D, R7D)
     and enhanced development near transit in low-density areas.
  3. Town Center Zoning — Commercial districts allow more residential.
  4. Accessory Dwelling Units (ADUs) — As-of-right in R1-R5 districts.
  5. Office-to-Residential Conversions — Expanded eligibility for buildings
     existing before Dec 31, 1990.
  6. Shared Housing (SROs) — Legalized in R6+ districts.
  7. Campus Infill — Institutional campuses can build housing.
  8. Landmark TDR — New Chair certification for air rights transfer (20% cap).

Sources:
  - Official ZR text as amended
  - HPD UAP Fact Sheet (April 2025)
  - DCP City of Yes Housing Opportunity page
"""

from __future__ import annotations

from app.zoning_engine.far_tables import (
    get_far_for_district,
    UAP_AFFORDABLE_FAR,
    get_uap_far,
    get_uap_bonus_far,
)
from app.zoning_engine.height_setback import get_height_rules


# ──────────────────────────────────────────────────────────────────
# UAP PROGRAM PARAMETERS
# ──────────────────────────────────────────────────────────────────

UAP_EFFECTIVE_DATE = "2024-12-05"
UAP_VESTING_DEADLINE = "2025-12-05"

# Affordability requirements for UAP
UAP_AFFORDABILITY = {
    "weighted_avg_ami": 60,          # Weighted average ≤60% AMI
    "max_single_band_ami": 100,      # No single band > 100% AMI
    "deep_affordability_threshold_sf": 10000,  # If AFA ≥ 10,000 SF
    "deep_affordability_ami": 40,    # At least 20% of AFA at ≤40% AMI
    "deep_affordability_pct": 0.20,  # 20% of affordable floor area
}

# UAP unit distribution requirements
UAP_DISTRIBUTION = {
    "vertical_pct": 0.65,           # Affordable units on ≥65% of residential stories
    "max_per_floor_pct": 0.667,     # No more than 2/3 of units on any floor
}

# UAP minimum unit sizes (from HPD)
UAP_MIN_UNIT_SIZES = {
    "studio": 400,
    "1br": 575,
    "2br": 775,
    "3br": 950,
}


# ──────────────────────────────────────────────────────────────────
# ADU (ACCESSORY DWELLING UNITS) PROVISIONS
# Available as-of-right in R1-R5 districts
# ──────────────────────────────────────────────────────────────────

ADU_ELIGIBLE_DISTRICTS = {
    "R1", "R1-1", "R1-2", "R1-2A",
    "R2", "R2A", "R2X",
    "R3-1", "R3-2", "R3A", "R3X",
    "R4", "R4-1", "R4A", "R4B",
    "R5", "R5A", "R5B", "R5D",
}

ADU_RULES = {
    "max_size_sf": 800,             # Max ADU size
    "max_units_per_lot": 1,         # One ADU per lot
    "conversion_only": False,       # New construction or conversion
    "detached_max_height_ft": 16,   # Max height for detached ADU
    "requires_owner_occupancy": False,  # No owner-occupancy requirement
}


# ──────────────────────────────────────────────────────────────────
# OFFICE-TO-RESIDENTIAL CONVERSION
# Expanded eligibility under City of Yes
# ──────────────────────────────────────────────────────────────────

OFFICE_CONVERSION_RULES = {
    "building_age_cutoff": "1990-12-31",  # Building must exist before this date
    "eligible_districts": [
        # M1 districts that allow conversion
        "M1-5", "M1-5A", "M1-5B", "M1-5M", "M1-6", "M1-6D", "M1-6M",
        # C5/C6 districts
        "C5-1", "C5-2", "C5-2.5", "C5-3", "C5-5", "C5-P",
        "C6-1", "C6-2", "C6-3", "C6-4", "C6-5", "C6-6", "C6-7", "C6-9",
    ],
    "min_floor_area_sf": 0,         # No minimum floor area threshold
    "residential_far_applies": True,  # Conversion subject to residential FAR
}


# ──────────────────────────────────────────────────────────────────
# LANDMARK TDR (Transfer of Development Rights)
# New Chair certification process (ZR 74-79)
# ──────────────────────────────────────────────────────────────────

LANDMARK_TDR_RULES = {
    "max_receiving_far_increase_pct": 0.20,  # Max 20% of receiving lot FAR
    "certification_process": "chair",  # Chair certification (no ULURP)
    "adjacency_required": False,  # Non-adjacent transfers allowed
    "contribution_required": True,  # Must contribute to landmark preservation
}


# ──────────────────────────────────────────────────────────────────
# SHARED HOUSING (SRO) PROVISIONS
# ──────────────────────────────────────────────────────────────────

SHARED_HOUSING_RULES = {
    "eligible_districts_min": "R6",  # R6 and above
    "min_unit_size_sf": 150,         # Minimum habitable room size
    "shared_kitchen_bath": True,     # Shared facilities allowed
}


# ──────────────────────────────────────────────────────────────────
# MAIN API FUNCTIONS
# ──────────────────────────────────────────────────────────────────

def calculate_uap_scenario(
    district: str,
    lot_area: float,
    street_width: str = "narrow",
) -> dict | None:
    """Calculate a UAP development scenario for a district.

    Returns None if the district is not eligible for UAP.

    Returns dict with:
        base_far, uap_far, bonus_far,
        base_zfa, uap_zfa, bonus_zfa,
        affordable_far, affordable_zfa,
        max_height, max_height_with_uap,
        affordability_requirements
    """
    uap_far = get_uap_far(district)
    if uap_far is None:
        return None

    base_data = get_far_for_district(district)
    res_far = base_data["residential"]
    if isinstance(res_far, dict):
        qh_val = res_far.get("qh", 0)
        # QH FAR may be street-width dependent (e.g. R6: wide=3.0, narrow=2.2)
        if isinstance(qh_val, dict):
            base_far = qh_val.get(street_width, qh_val.get("narrow", 0))
        else:
            base_far = qh_val
    elif res_far is not None:
        base_far = res_far
    else:
        return None

    bonus_far = uap_far - base_far
    affordable_far = bonus_far  # All bonus FAR must be affordable

    # Height rules: standard vs affordable
    height_standard = get_height_rules(district, street_width, is_affordable=False)
    height_affordable = get_height_rules(district, street_width, is_affordable=True)

    return {
        "base_far": base_far,
        "uap_far": uap_far,
        "bonus_far": round(bonus_far, 2),
        "base_zfa": round(base_far * lot_area),
        "uap_zfa": round(uap_far * lot_area),
        "bonus_zfa": round(bonus_far * lot_area),
        "affordable_far": round(affordable_far, 2),
        "affordable_zfa": round(affordable_far * lot_area),
        "max_height": height_standard.get("max_building_height"),
        "max_height_with_uap": height_affordable.get("max_building_height"),
        "affordability_requirements": UAP_AFFORDABILITY,
        "distribution_requirements": UAP_DISTRIBUTION,
        "min_unit_sizes": UAP_MIN_UNIT_SIZES,
    }


def is_adu_eligible(district: str) -> bool:
    """Check if a district is eligible for ADU construction."""
    return district.strip().upper() in ADU_ELIGIBLE_DISTRICTS


def get_adu_rules(district: str) -> dict | None:
    """Get ADU construction rules for an eligible district."""
    if not is_adu_eligible(district):
        return None
    return dict(ADU_RULES)


def is_office_conversion_eligible(
    district: str,
    building_year: int | None = None,
) -> bool:
    """Check if a site is eligible for office-to-residential conversion."""
    district = district.strip().upper()
    if district not in OFFICE_CONVERSION_RULES["eligible_districts"]:
        return False
    if building_year and building_year > 1990:
        return False
    return True


def get_city_of_yes_summary(
    district: str,
    lot_area: float = 0,
    borough: int = 0,
    community_district: int = 0,
    street_width: str = "narrow",
) -> dict:
    """Get a comprehensive summary of all City of Yes provisions applicable to a site.

    Returns dict with applicable provisions and their impacts.
    """
    district = district.strip().upper()

    from app.zoning_engine.parking import get_parking_zone

    provisions = {
        "city_of_yes_applicable": True,
        "effective_date": UAP_EFFECTIVE_DATE,
        "vesting_deadline": UAP_VESTING_DEADLINE,
        "provisions": [],
    }

    # UAP
    uap = calculate_uap_scenario(district, lot_area, street_width)
    if uap:
        provisions["provisions"].append({
            "name": "Universal Affordability Preference (UAP)",
            "applicable": True,
            "impact": f"+{uap['bonus_far']:.2f} FAR ({uap['bonus_zfa']:,.0f} SF) "
                      f"for affordable housing at avg ≤60% AMI",
            "details": uap,
        })

    # Parking zone
    zone = get_parking_zone(borough, community_district)
    zone_names = {
        0: "Manhattan Core (no residential parking)",
        1: "Inner Transit Zone (no residential parking)",
        2: "Outer Transit Zone (reduced parking with waivers)",
        3: "Beyond Greater Transit Zone (standard requirements)",
    }
    provisions["provisions"].append({
        "name": "Parking Reform",
        "applicable": zone <= 2,
        "impact": zone_names.get(zone, "Unknown zone"),
        "parking_zone": zone,
    })

    # ADU
    if is_adu_eligible(district):
        provisions["provisions"].append({
            "name": "Accessory Dwelling Unit (ADU)",
            "applicable": True,
            "impact": f"One ADU up to {ADU_RULES['max_size_sf']} SF permitted as-of-right",
            "details": ADU_RULES,
        })

    # Office conversion (check if commercial/manufacturing district)
    if district.startswith(("C", "M")):
        eligible = is_office_conversion_eligible(district)
        provisions["provisions"].append({
            "name": "Office-to-Residential Conversion",
            "applicable": eligible,
            "impact": "Buildings existing before Dec 31, 1990 may convert to residential"
                      if eligible else "Not eligible in this district",
        })

    return provisions
