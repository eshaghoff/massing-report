"""
NYC Zoning Resolution special district rules.

Special districts overlay the base zoning and can modify FAR, height,
setback, use, and other regulations. There are 60+ special districts
in NYC. This module covers the most impactful ones.

The PLUTO data fields spdist1, spdist2, spdist3 identify which special
district (if any) applies to a lot.
"""

from __future__ import annotations


# ──────────────────────────────────────────────────────────────────
# SPECIAL DISTRICT DEFINITIONS
# Key: PLUTO spdist code → rules
# ──────────────────────────────────────────────────────────────────

SPECIAL_DISTRICTS = {
    # ─── MIDTOWN (ZR Article VIII, Chapter 1) ───
    "MiD": {
        "name": "Special Midtown District",
        "description": "Core Midtown Manhattan (31st-61st, 3rd-8th Ave). "
                       "Mandatory daylight evaluation, specific tower setbacks, "
                       "FAR bonuses for public improvements.",
        "far_override": {
            # Sub-areas have different FARs; these are maximums
            "commercial_base": 15.0,
            "commercial_max_with_bonus": 21.6,
            "residential": 10.0,
            "cf": 15.0,
        },
        "height_override": None,  # Uses daylight evaluation instead of fixed heights
        "mandatory_improvements": True,
        "daylight_evaluation": True,
        "bonuses": {
            "public_plaza": {"max_additional_far": 3.0, "per_sf_ratio": 0.1},
            "subway_improvement": {"max_additional_far": 2.0},
            "theater_preservation": {"max_additional_far": 4.4},
        },
    },

    # ─── HUDSON YARDS (ZR 93-00) ───
    "HY": {
        "name": "Special Hudson Yards District",
        "description": "Far west side of Midtown. FARs up to 33.0 with "
                       "district improvement bonuses and mandatory IH.",
        "far_override": {
            "commercial_base": 10.0,
            "commercial_max_with_bonus": 33.0,
            "residential_base": 10.0,
            "residential_max_with_bonus": 26.0,
        },
        "mandatory_inclusionary": True,
    },

    # ─── LONG ISLAND CITY (ZR 117-00) ───
    "LIC": {
        "name": "Special Long Island City Mixed Use District",
        "description": "Queens waterfront. Mixed-use development with "
                       "residential and commercial at high densities.",
        "far_override": {
            "residential": 6.5,
            "commercial": 5.0,
            "cf": 6.5,
        },
    },

    # ─── DOWNTOWN BROOKLYN (ZR 101-00) ───
    "DB": {
        "name": "Special Downtown Brooklyn District",
        "description": "Downtown Brooklyn commercial/mixed-use core.",
        "far_override": {
            "commercial_base": 12.0,
            "commercial_max_with_bonus": 18.0,
            "residential": 12.0,
        },
        "mandatory_inclusionary": True,
    },

    # ─── EAST HARLEM CORRIDORS ───
    "EC": {
        "name": "Special East Harlem Corridors District",
        "description": "East Harlem rezoning with mandatory inclusionary housing.",
        "mandatory_inclusionary": True,
    },

    # ─── CLINTON (ZR 96-00) ───
    "CL": {
        "name": "Special Clinton District",
        "description": "Hell's Kitchen / Clinton. Preservation area with "
                       "anti-harassment protections.",
        "far_override": {
            "preservation_area_commercial": 5.0,
            "preservation_area_residential": 6.0,
            "perimeter_area": None,  # Follows base C6 zoning
        },
    },

    # ─── WEST CHELSEA (ZR 98-00) ───
    "WCh": {
        "name": "Special West Chelsea District",
        "description": "High Line corridor with TDR mechanisms.",
        "far_override": {
            "residential_base": 5.0,
            "residential_max_with_bonus": 7.5,
        },
        "tdr_available": True,
    },

    # ─── GARMENT CENTER (ZR 93-90) ───
    "GC": {
        "name": "Special Garment Center District",
        "description": "Garment district with manufacturing preservation requirements.",
    },

    # ─── TRIBECA MIXED USE ───
    "TMU": {
        "name": "Special TriBeCa Mixed Use District",
        "description": "TriBeCa loft district allowing residential conversion.",
    },

    # ─── SOUTH RICHMOND (Staten Island) ───
    "SRD": {
        "name": "Special South Richmond Development District",
        "description": "Planned development area in southern Staten Island.",
    },

    # ─── BAY RIDGE (Brooklyn) ───
    "BR": {
        "name": "Special Bay Ridge District",
        "description": "Bay Ridge special zoning with contextual rules.",
    },

    # ─── CONEY ISLAND ───
    "CI": {
        "name": "Special Coney Island District",
        "description": "Amusement and entertainment district.",
    },

    # ─── GOVERNORS ISLAND ───
    "GI": {
        "name": "Special Governors Island District",
        "description": "Special regulations for Governors Island redevelopment.",
    },
    # ─── FLUSHING WATERFRONT (ZR 129-00) ───
    "FW": {
        "name": "Special Flushing Waterfront District",
        "description": "Mixed-use waterfront area in Flushing with mandatory "
                       "affordable housing and height tiers.",
        "far_override": {
            "residential_base": 3.0,
            "residential_max_with_bonus": 6.0,
            "commercial": 2.0,
            "cf": 4.8,
        },
        "mandatory_inclusionary": True,
    },

    # ─── WILLETS POINT (ZR 124-00) ───
    "WP": {
        "name": "Special Willets Point District",
        "description": "Large-scale redevelopment area near Citi Field with "
                       "phased FAR and mandatory affordable housing.",
        "far_override": {
            "residential_base": 3.0,
            "residential_max_with_bonus": 6.9,
            "commercial_base": 2.0,
            "commercial_max_with_bonus": 5.0,
        },
        "mandatory_inclusionary": True,
    },

    # ─── HARLEM RIVER WATERFRONT (ZR 87-60) ───
    "HRW": {
        "name": "Special Harlem River Waterfront District",
        "description": "Bronx waterfront district requiring waterfront public "
                       "access and height controls.",
        "far_override": {
            "residential": 5.0,
            "commercial": 3.0,
            "cf": 5.0,
        },
    },

    # ─── BATTERY PARK CITY ───
    "BPC": {
        "name": "Battery Park City",
        "description": "Governed by BPC Authority master plan with unique "
                       "FAR, height, and use regulations.",
        "far_override": {
            "residential": 10.0,
            "commercial": 15.0,
            "cf": 10.0,
        },
    },

    # ─── LOWER MANHATTAN (ZR 91-00) ───
    "LM": {
        "name": "Special Lower Manhattan District",
        "description": "FAR bonuses and conversion incentives for Lower "
                       "Manhattan south of Chambers Street.",
        "far_override": {
            "commercial_base": 15.0,
            "commercial_max_with_bonus": 18.0,
            "residential": 12.0,
        },
        "bonuses": {
            "subway_improvement": {"max_additional_far": 3.0},
            "public_plaza": {"max_additional_far": 2.0},
        },
    },

    # ─── EAST MIDTOWN (ZR 81-60) ───
    "EM": {
        "name": "Special East Midtown Subdistrict",
        "description": "High-density commercial with TDR bank for landmark "
                       "preservation and public realm improvements.",
        "far_override": {
            "commercial_base": 15.0,
            "commercial_max_with_bonus": 27.0,
        },
        "tdr_available": True,
        "bonuses": {
            "landmark_tdr": {"max_additional_far": 12.0},
            "public_realm": {"max_additional_far": 3.0},
        },
    },

    # ─── 125TH STREET (ZR 97-00) ───
    "125": {
        "name": "Special 125th Street District",
        "description": "Mixed-use corridor along 125th Street with mandatory "
                       "inclusionary housing and height tiers.",
        "far_override": {
            "residential_base": 6.0,
            "residential_max_with_bonus": 9.0,
            "commercial": 6.0,
        },
        "mandatory_inclusionary": True,
    },

    # ─── COASTAL RISK (ZR Appendix A) ───
    "CR": {
        "name": "Coastal Flood Resilience Zone",
        "description": "Areas with flood resilience requirements including "
                       "freeboard, wet/dry floodproofing, and elevated utilities.",
    },

    # ─── ENHANCED COMMERCIAL ───
    "EC2": {
        "name": "Enhanced Commercial District",
        "description": "Various mapped areas with enhanced commercial FAR "
                       "and ground-floor retail requirements.",
        "far_override": {
            "commercial": 2.0,
        },
    },

}


def get_special_district_rules(spdist_code: str) -> dict | None:
    """Look up special district rules by PLUTO spdist code.

    Args:
        spdist_code: PLUTO special district code (e.g., "MiD", "HY")

    Returns:
        Dict of special district rules, or None if not a special district
    """
    if not spdist_code:
        return None

    spdist_code = spdist_code.strip()
    return SPECIAL_DISTRICTS.get(spdist_code)


def apply_special_district_overrides(
    base_far: dict,
    spdist_codes: list[str],
) -> dict:
    """Apply special district FAR overrides to base zoning.

    Args:
        base_far: Dict with residential, commercial, cf, manufacturing FARs
        spdist_codes: List of applicable special district codes

    Returns:
        Modified FAR dict with any special district overrides applied
    """
    result = dict(base_far)

    for code in spdist_codes:
        rules = get_special_district_rules(code)
        if not rules:
            continue

        overrides = rules.get("far_override")
        if not overrides:
            continue

        # Apply overrides (special district FAR takes precedence)
        if "commercial_base" in overrides:
            current = result.get("commercial") or 0
            result["commercial"] = max(current, overrides["commercial_base"])
        if "residential" in overrides and overrides["residential"]:
            current = result.get("residential") or 0
            if isinstance(current, dict):
                # HF/QH dict — use special district override as the new max
                result["residential"] = overrides["residential"]
            else:
                result["residential"] = max(current, overrides["residential"])
        if "cf" in overrides and overrides["cf"]:
            current = result.get("cf") or 0
            result["cf"] = max(current, overrides["cf"])

    return result


def get_special_district_bonuses(spdist_codes: list[str]) -> list[dict]:
    """Get available FAR bonuses from special districts.

    Returns list of bonus opportunities with their requirements.
    """
    bonuses = []

    for code in spdist_codes:
        rules = get_special_district_rules(code)
        if not rules:
            continue

        district_bonuses = rules.get("bonuses", {})
        for bonus_name, bonus_info in district_bonuses.items():
            bonuses.append({
                "source": rules["name"],
                "type": bonus_name.replace("_", " ").title(),
                "max_additional_far": bonus_info.get("max_additional_far", 0),
                "description": f"Bonus from {rules['name']}",
            })

    return bonuses
