"""
NYC Zoning Resolution floor area exemptions and deductions (ZR 12-10).

Certain spaces are exempt from floor area calculations:
- Cellar space (below grade on all sides)
- Accessory parking (below grade or in a parking structure)
- Mechanical space (boilers, HVAC, electrical, elevators above roof)
- Balconies (open, unenclosed, up to certain limits)
- Ground floor retail amenity space (in certain districts)
- Community facility bonus space (in certain mapped areas)
- Transit hall bonus space
- Lobby space (ground floor, up to limits)
- Laundry/storage rooms (in residential, limited)
- Enclosed bicycle parking (ZR 25-80)

These exemptions effectively increase what you can build within a given FAR.
"""

from __future__ import annotations


# Typical exemption percentages by building type
# These represent how much additional space (as % of ZFA) is exempt from FAR
EXEMPTION_ESTIMATES = {
    # Residential buildings
    "residential_walkup": {
        "cellar": 0.10,           # Full cellar doesn't count
        "mechanical": 0.03,       # Boiler, electrical rooms
        "parking_below_grade": 0, # If present, fully exempt
        "laundry_storage": 0.02,  # Laundry, storage, bike rooms
        "balconies": 0.02,        # Open balconies exempt
        "total_typical": 0.17,
    },
    "residential_elevator": {
        "cellar": 0.08,
        "mechanical": 0.04,       # More MEP in taller buildings
        "parking_below_grade": 0,
        "laundry_storage": 0.02,
        "balconies": 0.02,
        "elevator_bulkhead": 0.01,
        "total_typical": 0.17,
    },
    "residential_tower": {
        "cellar": 0.06,
        "mechanical": 0.05,       # Mechanical floors exempt
        "parking_below_grade": 0,
        "laundry_storage": 0.01,
        "balconies": 0.02,
        "elevator_bulkhead": 0.01,
        "total_typical": 0.15,
    },
    "commercial_office": {
        "cellar": 0.05,
        "mechanical": 0.06,       # HVAC floors, electrical
        "parking_below_grade": 0,
        "loading": 0.01,
        "lobby_transit": 0.03,    # Ground floor lobby exempt portion
        "total_typical": 0.15,
    },
    "mixed_use": {
        "cellar": 0.07,
        "mechanical": 0.05,
        "parking_below_grade": 0,
        "laundry_storage": 0.01,
        "loading": 0.01,
        "total_typical": 0.14,
    },
}


def calculate_exempt_area(
    zoning_floor_area: float,
    building_type: str = "residential_elevator",
    has_cellar: bool = True,
    parking_sf_below_grade: float = 0,
    mechanical_floors: int = 0,
    mechanical_sf_per_floor: float = 0,
) -> dict:
    """Calculate exempt floor area for a building.

    Args:
        zoning_floor_area: Total zoning floor area (FAR * lot area)
        building_type: One of the keys in EXEMPTION_ESTIMATES
        has_cellar: Whether the building has a cellar
        parking_sf_below_grade: Below-grade parking area in SF
        mechanical_floors: Number of dedicated mechanical floors
        mechanical_sf_per_floor: SF per mechanical floor

    Returns dict with:
        total_exempt_sf: total exempt area
        gross_building_area: ZFA + exempt area (what you actually build)
        breakdown: detailed breakdown of exempt areas
    """
    estimates = EXEMPTION_ESTIMATES.get(building_type, EXEMPTION_ESTIMATES["residential_elevator"])

    breakdown = {}

    # Cellar: fully exempt if below grade on all sides
    cellar_sf = 0
    if has_cellar:
        cellar_sf = zoning_floor_area * estimates.get("cellar", 0.08)
    breakdown["cellar"] = cellar_sf

    # Parking below grade: fully exempt
    breakdown["parking_below_grade"] = parking_sf_below_grade

    # Mechanical: exempt if in dedicated spaces
    mech_sf = mechanical_floors * mechanical_sf_per_floor if mechanical_floors else (
        zoning_floor_area * estimates.get("mechanical", 0.04)
    )
    breakdown["mechanical"] = mech_sf

    # Other standard exemptions
    for key in ["laundry_storage", "balconies", "elevator_bulkhead", "loading", "lobby_transit"]:
        pct = estimates.get(key, 0)
        if pct > 0:
            breakdown[key] = zoning_floor_area * pct

    total_exempt = sum(breakdown.values())

    return {
        "total_exempt_sf": round(total_exempt),
        "gross_building_area": round(zoning_floor_area + total_exempt),
        "breakdown": {k: round(v) for k, v in breakdown.items()},
        "exemption_ratio": round(total_exempt / zoning_floor_area, 3) if zoning_floor_area > 0 else 0,
    }


# ──────────────────────────────────────────────────────────────────
# Specific exemption rules by zoning section
# ──────────────────────────────────────────────────────────────────

def is_cellar_exempt(below_grade_on_all_sides: bool) -> bool:
    """ZR 12-10: Cellar space is exempt from floor area if the floor level
    is below curb level on ALL sides of the building."""
    return below_grade_on_all_sides


def get_balcony_exemption(district: str) -> dict:
    """ZR 23-13: Balcony rules vary by district.

    In Quality Housing buildings:
    - Recessed balconies up to 8% of floor area per floor are exempt
    - Balconies must be recessed behind the building wall
    """
    return {
        "max_exempt_pct_per_floor": 0.08,
        "must_be_recessed": True,
        "min_depth": 5,  # feet
        "min_width": 6,  # feet
    }


def get_mechanical_deduction_rules() -> dict:
    """ZR 12-10: Mechanical equipment floor area deductions.

    Floor area used for mechanical equipment is exempt:
    - Boiler rooms, HVAC systems, electrical switchgear
    - Elevator machinery above roof level (bulkheads)
    - Water tanks
    - Dedicated mechanical floors (in tall buildings)
    """
    return {
        "boiler_room": True,
        "hvac_equipment": True,
        "electrical_rooms": True,
        "elevator_bulkhead": True,
        "water_tanks": True,
        "mechanical_floors": True,
        "typical_pct_of_gross": 0.04,  # 3-5% of gross area
    }
