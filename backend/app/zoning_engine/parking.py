"""
NYC Zoning Resolution parking requirements.

Updated to reflect City of Yes for Housing Opportunity (adopted Dec 5, 2024).

City of Yes created a new multi-zone parking system:
  - Manhattan Core (CDs 1-8): No residential parking (pre-existing)
  - Inner Transit Zone: No residential parking required
  - Outer Transit Zone: Reduced parking, generous waivers
  - Beyond Greater Transit Zone: Previous requirements apply

Includes:
  - Automobile parking (ZR 25-20 through 25-30)
  - City of Yes transit zone system (ZR 25-211, 25-212, 25-22, 25-241)
  - Accessible parking (ADA / NYC Building Code)
  - Bicycle parking (ZR 25-80)
  - Loading berths (ZR 36-60)

Sources:
  - ZR Article II, Chapter 5 as amended
  - City of Yes for Housing Opportunity (ULURP N 240187 ZRY)
"""

from __future__ import annotations

import re


# ──────────────────────────────────────────────────────────────────
# CITY OF YES PARKING ZONES (effective Dec 5, 2024)
#
# Zone 0: Manhattan Core (CDs 1-8) — No residential parking
# Zone 1: Inner Transit Zone — No residential parking
# Zone 2: Outer Transit Zone — Reduced parking with waivers
# Zone 3: Beyond Greater Transit Zone — Previous requirements
# ──────────────────────────────────────────────────────────────────

# Manhattan Core: CDs 1-8 (below ~110th St approx)
# Represented as borough 1, CDs 101-108
MANHATTAN_CORE_CDS = {101, 102, 103, 104, 105, 106, 107, 108}

# Inner Transit Zone community districts
# Manhattan CDs 9-11 (already covered since borough 1 = all Manhattan)
# Brooklyn CDs 1, 2, 3, 6 (part), 7, 8
# Queens CDs 1, 2, 3 (part), 4 (part)
INNER_TRANSIT_ZONE_CDS = {
    # Manhattan CDs 9-12 (not in core but in inner transit)
    109, 110, 111, 112,
    # Brooklyn
    301, 302, 303, 306, 307, 308,
    # Queens (Long Island City + western Queens)
    401, 402,
}

# Outer Transit Zone: within 0.5 mi of subway, 0.25 mi of LIRR/MetroNorth
# These are the community districts in the outer transit zone.
# The actual boundaries are mapped by DCP; we use CD approximations.
OUTER_TRANSIT_ZONE_CDS = {
    # Brooklyn
    304, 305, 309, 310, 312, 314, 315, 316, 317, 318,
    # Queens
    403, 404, 405, 406, 407, 408, 412, 414,
    # Bronx
    201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212,
    # Staten Island (limited, near rail stations)
    501,
}

# Special exemption areas where council members maintained existing parking
# (ZR 25-241 special areas)
PARKING_EXEMPTION_AREAS = {
    # These CDs maintain existing (pre-CoY) parking requirements
    # Parts of north Bronx, Rockaway, Corona
    # We flag these but actual boundaries are sub-CD level
}


# ──────────────────────────────────────────────────────────────────
# RESIDENTIAL AUTOMOBILE PARKING (ZR 25-20)
# Spaces per dwelling unit — BASE rates (pre-transit zone reduction)
# ──────────────────────────────────────────────────────────────────

RESIDENTIAL_PARKING_RATIOS = {
    "R1": 1.0,  "R2": 1.0,  "R3": 1.0,  "R4": 1.0,  "R4A": 1.0, "R4B": 1.0,
    "R5": 0.85, "R5A": 0.85, "R5B": 0.85, "R5D": 0.50,
    "R6": 0.70, "R6A": 0.50, "R6B": 0.50, "R6D": 0.50,
    "R7": 0.50, "R7-1": 0.50, "R7-2": 0.50,
    "R7A": 0.50, "R7B": 0.50, "R7D": 0.40, "R7X": 0.40,
    "R8": 0.40, "R8A": 0.40, "R8B": 0.40, "R8X": 0.40,
    "R9": 0.40, "R9A": 0.40, "R9X": 0.40, "R9D": 0.40,
    "R10": 0.40, "R10A": 0.40, "R10X": 0.40,
    "R11": 0.40, "R12": 0.40,
}

# ──────────────────────────────────────────────────────────────────
# OUTER TRANSIT ZONE PARKING RATIOS (City of Yes)
# Reduced ratios for Outer Transit Zone (% of dwelling units)
# ──────────────────────────────────────────────────────────────────

OUTER_TRANSIT_ZONE_RATIOS = {
    # district_base: (ratio, waiver_threshold)
    # ratio = spaces per DU; waiver_threshold = if required spaces ≤ this, no parking
    "R5":  (0.50, 10),
    "R6":  (0.25, 15),
    "R7":  (0.25, 15),
    "R8":  (0.20, 15),
    "R9":  (0.20, 15),
    "R10": (0.20, 15),
    "R11": (0.20, 15),
    "R12": (0.20, 15),
}

# ──────────────────────────────────────────────────────────────────
# COMMERCIAL AUTOMOBILE PARKING (ZR 36-21)
# Spaces per 1,000 SF
# ──────────────────────────────────────────────────────────────────

COMMERCIAL_PARKING_RATIOS = {
    "retail": {
        "R1": 3.3, "R2": 3.3, "R3": 3.3, "R4": 3.3, "R5": 3.3,
        "R6": 1.0, "R7": 1.0, "R8": 1.0, "R9": 1.0, "R10": 0,
        "C1": 3.3, "C2": 3.3, "C3": 1.0, "C4": 1.0,
        "C5": 0, "C6": 0, "C7": 1.0, "C8": 1.0,
    },
    "office": {
        "C5": 0, "C6": 0, "C4": 1.0,
    },
}

# ──────────────────────────────────────────────────────────────────
# BICYCLE PARKING (ZR 25-80)
# Required for new buildings and enlargements
# ──────────────────────────────────────────────────────────────────

BICYCLE_PARKING = {
    # Residential: 1 space per DU for first 200 units,
    # then 1 per 2 DU for units 201+
    "residential": {
        "first_200_ratio": 1.0,    # 1 space per unit
        "above_200_ratio": 0.5,    # 1 space per 2 units
    },
    # Commercial: 1 space per 10,000 SF (office), varies by use
    "commercial_office": {
        "ratio_per_sf": 1 / 10000,
        "min_spaces": 1,
    },
    "commercial_retail": {
        "ratio_per_sf": 1 / 10000,
        "min_spaces": 1,
    },
    "community_facility": {
        "ratio_per_sf": 1 / 10000,
        "min_spaces": 1,
    },
}

# Bicycle parking space dimensions (ZR 25-80)
BIKE_SPACE_SF = 18  # SF per bike space (6ft x 3ft including access aisle)
BIKE_ROOM_OVERHEAD = 1.3  # 30% extra for circulation in bike room


# ──────────────────────────────────────────────────────────────────
# LOADING BERTHS (ZR 36-60 series)
# Required for buildings over certain floor area thresholds
# ──────────────────────────────────────────────────────────────────

LOADING_BERTH_REQUIREMENTS = {
    # {use: [(min_sf_threshold, berths_required), ...]}
    "residential": [
        (25000, 0),
        (100000, 1),
        (200000, 2),
        (500000, 3),
        (800000, 4),
    ],
    "commercial_retail": [
        (8000, 0),
        (25000, 1),
        (40000, 2),
        (60000, 3),
        (100000, 4),
    ],
    "commercial_office": [
        (25000, 0),
        (100000, 1),
        (200000, 2),
        (500000, 3),
        (800000, 4),
    ],
    "community_facility": [
        (25000, 0),
        (100000, 1),
        (200000, 2),
    ],
}

# Loading berth dimensions
LOADING_BERTH_DIMS = {
    "standard": {"width": 12, "depth": 33, "height": 14, "sf": 396},
    "large": {"width": 12, "depth": 50, "height": 14, "sf": 600},
}


# ──────────────────────────────────────────────────────────────────
# ACCESSIBLE PARKING (ADA / NYC Building Code)
# ──────────────────────────────────────────────────────────────────

def get_accessible_spaces(total_spaces: int) -> int:
    """Calculate required accessible parking spaces per ADA/NYC Building Code.

    Based on total required parking spaces:
      1-25 spaces:   1 accessible
      26-50:         2
      51-75:         3
      76-100:        4
      101-150:       5
      151-200:       6
      201-300:       7
      301-400:       8
      401-500:       9
      501-1000:      2% of total
      1001+:         20 + 1 per 100 above 1000
    """
    if total_spaces <= 0:
        return 0
    if total_spaces <= 25:
        return 1
    if total_spaces <= 50:
        return 2
    if total_spaces <= 75:
        return 3
    if total_spaces <= 100:
        return 4
    if total_spaces <= 150:
        return 5
    if total_spaces <= 200:
        return 6
    if total_spaces <= 300:
        return 7
    if total_spaces <= 400:
        return 8
    if total_spaces <= 500:
        return 9
    if total_spaces <= 1000:
        return max(10, int(total_spaces * 0.02))
    return 20 + (total_spaces - 1000) // 100


def get_parking_zone(borough: int, community_district: int) -> int:
    """Determine the City of Yes parking zone for a location.

    Returns:
        0 = Manhattan Core (CDs 1-8): No residential parking
        1 = Inner Transit Zone: No residential parking
        2 = Outer Transit Zone: Reduced parking with waivers
        3 = Beyond Greater Transit Zone: Standard requirements
    """
    # Construct CD identifier as borough*100 + cd_number
    if community_district > 100:
        cd_id = community_district  # Already in borough*100+cd format
    else:
        cd_id = borough * 100 + community_district

    # Manhattan Core (CDs 1-8)
    if borough == 1 and cd_id in MANHATTAN_CORE_CDS:
        return 0

    # Inner Transit Zone
    if borough == 1:
        # All of Manhattan is Zone 0 or Zone 1
        return 1
    if cd_id in INNER_TRANSIT_ZONE_CDS:
        return 1

    # Outer Transit Zone
    if cd_id in OUTER_TRANSIT_ZONE_CDS:
        return 2

    # Beyond Greater Transit Zone
    return 3


def calculate_bicycle_parking(
    unit_count: int = 0,
    commercial_sf: float = 0,
    cf_sf: float = 0,
    use_type: str = "residential",
) -> dict:
    """Calculate bicycle parking requirements (ZR 25-80).

    Args:
        unit_count: Number of dwelling units
        commercial_sf: Commercial floor area in SF
        cf_sf: Community facility floor area in SF
        use_type: Primary use type

    Returns dict with:
        residential_bike_spaces, commercial_bike_spaces,
        total_bike_spaces, bike_room_sf
    """
    res_spaces = 0
    if unit_count > 0:
        rules = BICYCLE_PARKING["residential"]
        if unit_count <= 200:
            res_spaces = int(unit_count * rules["first_200_ratio"])
        else:
            res_spaces = 200 + int((unit_count - 200) * rules["above_200_ratio"])

    comm_spaces = 0
    if commercial_sf > 0:
        rules = BICYCLE_PARKING.get("commercial_office", {})
        comm_spaces = max(
            rules.get("min_spaces", 1),
            int(commercial_sf * rules.get("ratio_per_sf", 1/10000)),
        )

    cf_spaces = 0
    if cf_sf > 0:
        rules = BICYCLE_PARKING["community_facility"]
        cf_spaces = max(
            rules.get("min_spaces", 1),
            int(cf_sf * rules.get("ratio_per_sf", 1/10000)),
        )

    total = res_spaces + comm_spaces + cf_spaces
    bike_room_sf = int(total * BIKE_SPACE_SF * BIKE_ROOM_OVERHEAD)

    return {
        "residential_bike_spaces": res_spaces,
        "commercial_bike_spaces": comm_spaces,
        "cf_bike_spaces": cf_spaces,
        "total_bike_spaces": total,
        "bike_room_sf": bike_room_sf,
    }


def calculate_loading_berths(
    residential_sf: float = 0,
    commercial_sf: float = 0,
    cf_sf: float = 0,
    commercial_type: str = "retail",
) -> dict:
    """Calculate loading berth requirements (ZR 36-60).

    Args:
        residential_sf: Residential floor area in SF
        commercial_sf: Commercial floor area in SF
        cf_sf: Community facility floor area in SF
        commercial_type: "retail" or "office"

    Returns dict with:
        residential_berths, commercial_berths, cf_berths,
        total_berths, total_loading_sf
    """
    res_berths = _get_berths_for_area(residential_sf, "residential")
    comm_key = f"commercial_{commercial_type}"
    comm_berths = _get_berths_for_area(commercial_sf, comm_key)
    cf_berths = _get_berths_for_area(cf_sf, "community_facility")

    total = res_berths + comm_berths + cf_berths
    total_sf = total * LOADING_BERTH_DIMS["standard"]["sf"]

    return {
        "residential_berths": res_berths,
        "commercial_berths": comm_berths,
        "cf_berths": cf_berths,
        "total_berths": total,
        "total_loading_sf": total_sf,
        "berth_dimensions": LOADING_BERTH_DIMS["standard"],
    }


def _get_berths_for_area(floor_area: float, use_type: str) -> int:
    """Look up required berths for a given floor area and use type."""
    thresholds = LOADING_BERTH_REQUIREMENTS.get(use_type, [])
    berths = 0
    for threshold, required in thresholds:
        if floor_area >= threshold:
            berths = required
    return berths


def calculate_parking(
    district: str,
    unit_count: int = 0,
    commercial_sf: float = 0,
    cf_sf: float = 0,
    lot_area: float = 0,
    borough: int = 0,
    community_district: int = 0,
    is_transit_zone: bool = False,
    affordable_units: int = 0,
) -> dict:
    """Calculate comprehensive parking requirements.

    Implements the City of Yes four-zone parking system.

    Args:
        district: Zoning district code
        unit_count: Total dwelling units (market-rate + affordable)
        commercial_sf: Commercial floor area
        cf_sf: Community facility floor area
        lot_area: Lot area in SF
        borough: NYC borough (1=Manhattan, 2=Bronx, 3=Brooklyn, 4=Queens, 5=SI)
        community_district: Community district number
        is_transit_zone: Legacy flag (still used for backwards compatibility)
        affordable_units: Number of affordable/income-restricted units (no parking req under CoY)

    Returns dict with:
        residential_spaces_required, commercial_spaces_required,
        total_spaces_required, accessible_spaces_required,
        waiver_eligible, parking_zone, parking_zone_name,
        parking_options, bicycle_parking, loading_berths
    """
    district = district.strip().upper()
    base = _get_base_district(district)

    # ── Determine parking zone ──
    zone = get_parking_zone(borough, community_district)

    # Legacy is_transit_zone flag: if explicitly set, use zone 1 minimum
    if is_transit_zone and zone > 1:
        zone = 1

    zone_names = {
        0: "Manhattan Core",
        1: "Inner Transit Zone",
        2: "Outer Transit Zone",
        3: "Beyond Greater Transit Zone",
    }

    # ── Residential automobile parking ──
    # Under City of Yes, affordable units have NO parking requirement
    market_rate_units = max(0, unit_count - affordable_units)

    if zone == 0 or zone == 1:
        # Manhattan Core + Inner Transit Zone: no residential parking
        res_spaces = 0
    elif zone == 2:
        # Outer Transit Zone: reduced ratios with waivers
        otz = OUTER_TRANSIT_ZONE_RATIOS.get(base, (0.25, 15))
        ratio, waiver_threshold = otz
        res_spaces = int(round(market_rate_units * ratio))
        if res_spaces <= waiver_threshold:
            res_spaces = 0  # As-of-right waiver
    else:
        # Beyond Greater Transit Zone: standard ratios
        ratio = RESIDENTIAL_PARKING_RATIOS.get(district)
        if ratio is None:
            ratio = RESIDENTIAL_PARKING_RATIOS.get(base, 0.5)
        res_spaces = int(round(market_rate_units * ratio))

    # ── Commercial automobile parking ──
    comm_spaces = 0
    if commercial_sf > 0:
        if zone <= 1:
            # No commercial parking in Manhattan Core / Inner Transit Zone
            comm_spaces = 0
        else:
            retail_ratios = COMMERCIAL_PARKING_RATIOS["retail"]
            comm_ratio = retail_ratios.get(base, 1.0)
            if zone == 2:
                comm_ratio *= 0.5  # Outer transit zone reduces commercial too
            comm_spaces = int(round(commercial_sf / 1000 * comm_ratio))

    total = res_spaces + comm_spaces

    # ── Accessible spaces ──
    accessible = get_accessible_spaces(total)

    # ── Waiver eligibility ──
    waiver = False
    # Small lot waiver (ZR 25-26, still applies in zone 3)
    if zone >= 3:
        if base in ("R5", "R6", "R7"):
            if lot_area < 10000:
                waiver = True
        if base in ("R8", "R9", "R10", "R11", "R12"):
            if lot_area < 15000:
                waiver = True
        # 10-unit waiver
        if unit_count <= 10 and base in ("R6", "R7", "R8", "R9", "R10", "R11", "R12"):
            waiver = True
    elif zone == 2:
        # Outer transit zone: already has built-in waivers above
        waiver = (total == 0)

    # ── Bicycle parking ──
    bike = calculate_bicycle_parking(unit_count, commercial_sf, cf_sf)

    # ── Loading berths ──
    loading = calculate_loading_berths(
        residential_sf=unit_count * 700,  # Estimate residential SF
        commercial_sf=commercial_sf,
        cf_sf=cf_sf,
    )

    # ── Build parking layout options ──
    options = _build_parking_options(total, lot_area)

    return {
        "residential_spaces_required": res_spaces,
        "commercial_spaces_required": comm_spaces,
        "total_spaces_required": total,
        "accessible_spaces_required": accessible,
        "waiver_eligible": waiver,
        "parking_zone": zone,
        "parking_zone_name": zone_names.get(zone, "Unknown"),
        "in_transit_zone": zone <= 1,  # Backwards compatibility
        "parking_options": options,
        "bicycle_parking": bike,
        "loading_berths": loading,
    }


def _get_base_district(district: str) -> str:
    match = re.match(r'^(R\d+|C\d+|M\d+)', district)
    if match:
        return match.group(1)
    return district


def _build_parking_options(total_spaces: int, lot_area: float) -> list[dict]:
    if total_spaces == 0:
        return []

    options = []

    # Below-grade option
    sf_per_space = 350
    ramp_sf = int(total_spaces * sf_per_space * 0.15)
    total_sf = total_spaces * sf_per_space + ramp_sf
    options.append({
        "type": "below_grade",
        "sf_per_space": sf_per_space,
        "total_sf": total_sf,
        "ramp_sf": ramp_sf,
        "estimated_cost": total_spaces * 80000,  # $80K per space below grade
    })

    # At-grade option
    at_grade_sf = total_spaces * 350
    floors = at_grade_sf / lot_area if lot_area > 0 else 1
    options.append({
        "type": "at_grade",
        "sf_per_space": 350,
        "total_sf": at_grade_sf,
        "floors_consumed": round(floors, 2),
    })

    # Mechanical stackers
    stacker_sf = total_spaces * 200
    options.append({
        "type": "mechanical_stackers",
        "sf_per_space": 200,
        "total_sf": stacker_sf,
        "estimated_cost": total_spaces * 35000,
    })

    # Ramp to second floor
    ramp_struct_sf = 1200  # ramp structure
    ramp_total_sf = total_spaces * 375 + ramp_struct_sf
    options.append({
        "type": "ramp_to_second_floor",
        "sf_per_space": 375,
        "total_sf": ramp_total_sf,
    })

    return options
