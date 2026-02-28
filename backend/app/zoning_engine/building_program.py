"""
Building program calculator.

Takes a DevelopmentScenario and generates a detailed building program with:
  - Core sizing (stairs, elevators, trash, MEP, corridors)
  - Ground floor program (lobby, mail, package, bike storage, etc.)
  - Cellar/mechanical program (boiler, pumps, storage, laundry)
  - Bulkhead/roof (stair bulkheads, elevator bulkheads, mechanical penthouse)
  - Loss factor calculation (gross → net rentable)
  - Unit mix generation (maximize, balanced, family)

The loss factor benchmarks:
  Walk-up (≤6 floors):  10-15%
  Mid-rise (7-12):      15-20%
  High-rise (13+):      18-25%
  Tower (25+):          22-30%
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.zoning_engine.parking import calculate_bicycle_parking


# ──────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────

@dataclass
class CoreSizing:
    """Vertical circulation and services per floor."""
    stairs: int
    stair_sf_per_floor: float
    elevators: int
    elevator_sf_per_floor: float
    freight_elevators: int
    freight_elevator_sf_per_floor: float
    trash_chute_sf_per_floor: float
    mep_closet_sf_per_floor: float
    fire_riser_sf_per_floor: float
    corridor_sf_per_floor: float
    total_core_sf_per_floor: float
    core_percentage: float  # of typical floor footprint

    def to_dict(self) -> dict:
        return {
            "stairs": self.stairs,
            "stair_sf_per_floor": self.stair_sf_per_floor,
            "elevators": self.elevators,
            "elevator_sf_per_floor": self.elevator_sf_per_floor,
            "freight_elevators": self.freight_elevators,
            "freight_elevator_sf_per_floor": self.freight_elevator_sf_per_floor,
            "trash_chute_sf_per_floor": self.trash_chute_sf_per_floor,
            "mep_closet_sf_per_floor": self.mep_closet_sf_per_floor,
            "fire_riser_sf_per_floor": self.fire_riser_sf_per_floor,
            "corridor_sf_per_floor": self.corridor_sf_per_floor,
            "total_core_sf_per_floor": self.total_core_sf_per_floor,
            "core_percentage": self.core_percentage,
        }


@dataclass
class GroundFloorProgram:
    """Ground floor non-rentable program areas."""
    lobby_sf: float
    mailroom_sf: float
    package_room_sf: float
    super_office_sf: float
    electrical_meter_sf: float
    fire_pump_room_sf: float  # 0 if building ≤ 75 ft
    bike_storage_sf: float
    trash_collection_sf: float
    total_sf: float

    def to_dict(self) -> dict:
        return {
            "lobby_sf": self.lobby_sf,
            "mailroom_sf": self.mailroom_sf,
            "package_room_sf": self.package_room_sf,
            "super_office_sf": self.super_office_sf,
            "electrical_meter_sf": self.electrical_meter_sf,
            "fire_pump_room_sf": self.fire_pump_room_sf,
            "bike_storage_sf": self.bike_storage_sf,
            "trash_collection_sf": self.trash_collection_sf,
            "total_sf": self.total_sf,
        }


@dataclass
class CellarProgram:
    """Cellar / sub-grade mechanical program."""
    boiler_room_sf: float
    water_pump_room_sf: float
    sprinkler_room_sf: float
    resident_storage_sf: float
    laundry_sf: float
    total_sf: float

    def to_dict(self) -> dict:
        return {
            "boiler_room_sf": self.boiler_room_sf,
            "water_pump_room_sf": self.water_pump_room_sf,
            "sprinkler_room_sf": self.sprinkler_room_sf,
            "resident_storage_sf": self.resident_storage_sf,
            "laundry_sf": self.laundry_sf,
            "total_sf": self.total_sf,
        }


@dataclass
class BulkheadProgram:
    """Roof bulkheads and mechanical penthouse (permitted obstructions)."""
    stair_bulkhead_sf: float
    elevator_bulkhead_sf: float
    mechanical_penthouse_sf: float
    total_sf: float

    def to_dict(self) -> dict:
        return {
            "stair_bulkhead_sf": self.stair_bulkhead_sf,
            "elevator_bulkhead_sf": self.elevator_bulkhead_sf,
            "mechanical_penthouse_sf": self.mechanical_penthouse_sf,
            "total_sf": self.total_sf,
        }


@dataclass
class UnitMixOption:
    """One unit mix configuration."""
    strategy: str  # "maximize", "balanced", "family"
    units: list[dict]  # [{"type": "studio", "count": 5, "avg_sf": 425}, ...]
    total_units: int
    average_unit_sf: float
    exceeds_du_limit: bool
    du_limit: int | None

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "units": self.units,
            "total_units": self.total_units,
            "average_unit_sf": self.average_unit_sf,
            "exceeds_du_limit": self.exceeds_du_limit,
            "du_limit": self.du_limit,
        }


@dataclass
class BuildingProgram:
    """Complete building program output."""
    gross_building_area: float
    zoning_floor_area: float
    mechanical_deductions: float
    gross_above_grade: float

    core: CoreSizing
    ground_floor: GroundFloorProgram
    cellar: CellarProgram
    bulkhead: BulkheadProgram

    total_core_area: float  # core × floors
    net_rentable_residential: float
    net_rentable_commercial: float
    loss_factor_pct: float
    efficiency_ratio: float

    unit_mix_options: list[UnitMixOption]

    num_floors: int
    max_height_ft: float
    building_class: str  # "walkup", "midrise", "highrise", "tower"

    def to_dict(self) -> dict:
        return {
            "gross_building_area": self.gross_building_area,
            "zoning_floor_area": self.zoning_floor_area,
            "mechanical_deductions": self.mechanical_deductions,
            "gross_above_grade": self.gross_above_grade,
            "core": self.core.to_dict(),
            "ground_floor": self.ground_floor.to_dict(),
            "cellar": self.cellar.to_dict(),
            "bulkhead": self.bulkhead.to_dict(),
            "total_core_area": self.total_core_area,
            "net_rentable_residential": self.net_rentable_residential,
            "net_rentable_commercial": self.net_rentable_commercial,
            "loss_factor_pct": self.loss_factor_pct,
            "efficiency_ratio": self.efficiency_ratio,
            "unit_mix_options": [m.to_dict() for m in self.unit_mix_options],
            "num_floors": self.num_floors,
            "max_height_ft": self.max_height_ft,
            "building_class": self.building_class,
        }


# ──────────────────────────────────────────────────────────────────
# UNIT SIZE STANDARDS (NYC market norms)
# ──────────────────────────────────────────────────────────────────

UNIT_SIZES = {
    "studio": 425,
    "1br": 625,
    "2br": 875,
    "3br": 1100,
}

UNIT_MIX_STRATEGIES = {
    "maximize": {"studio": 0.40, "1br": 0.40, "2br": 0.15, "3br": 0.05},
    "balanced": {"studio": 0.15, "1br": 0.45, "2br": 0.30, "3br": 0.10},
    "family":   {"studio": 0.05, "1br": 0.20, "2br": 0.45, "3br": 0.30},
}


# ──────────────────────────────────────────────────────────────────
# CORE SIZING
# ──────────────────────────────────────────────────────────────────

def calculate_core(
    num_floors: int,
    total_units: int,
    typical_floor_sf: float,
    building_depth: float = 100,
    corridor_type: str = "double_loaded",
) -> CoreSizing:
    """Calculate building core requirements.

    Args:
        num_floors: Number of above-grade floors
        total_units: Total dwelling units
        typical_floor_sf: Gross SF of a typical floor
        building_depth: Building depth in feet (for corridor length calc)
        corridor_type: "double_loaded" or "single_loaded"
    """
    # Stairs — NYC single-stair reform (effective 2024):
    # Buildings ≤6 stories with floor plates ≤4,000 SF can use single staircase
    if num_floors <= 6 and typical_floor_sf <= 4000:
        stairs = 1
    elif num_floors <= 30:
        stairs = 2
    else:
        stairs = 3
    stair_sf = stairs * 150  # 150 SF per stair per floor

    # Elevators — BC 3002.4: min 1 for 5+ stories
    if num_floors < 5:
        elevators = 0
    elif num_floors <= 8:
        elevators = 1
    elif num_floors <= 16:
        elevators = 2
    elif num_floors <= 24:
        elevators = 3
    else:
        elevators = max(3, math.ceil(num_floors / 8))
    elevator_sf = elevators * 75  # 75 SF per elevator per floor

    # Freight/service elevator for 10+ floors
    freight = 1 if num_floors >= 10 else 0
    freight_sf = freight * 90

    # Trash chute + room per floor
    trash_sf = 80.0

    # MEP closet per floor
    mep_sf = 60.0

    # Fire riser
    fire_sf = 15.0

    # Corridor: 5.5 ft wide × building depth
    # Double-loaded (units on both sides) = full depth
    # Single-loaded = half depth
    corridor_length = building_depth if corridor_type == "double_loaded" else building_depth / 2
    corridor_sf = 5.5 * corridor_length
    # Cap corridor at 15% of typical floor (small buildings don't need huge corridors)
    if typical_floor_sf > 0:
        corridor_sf = min(corridor_sf, typical_floor_sf * 0.15)

    total_core = stair_sf + elevator_sf + freight_sf + trash_sf + mep_sf + fire_sf + corridor_sf
    core_pct = (total_core / typical_floor_sf * 100) if typical_floor_sf > 0 else 0

    return CoreSizing(
        stairs=stairs,
        stair_sf_per_floor=stair_sf,
        elevators=elevators,
        elevator_sf_per_floor=elevator_sf,
        freight_elevators=freight,
        freight_elevator_sf_per_floor=freight_sf,
        trash_chute_sf_per_floor=trash_sf,
        mep_closet_sf_per_floor=mep_sf,
        fire_riser_sf_per_floor=fire_sf,
        corridor_sf_per_floor=round(corridor_sf, 1),
        total_core_sf_per_floor=round(total_core, 1),
        core_percentage=round(core_pct, 1),
    )


# ──────────────────────────────────────────────────────────────────
# GROUND FLOOR PROGRAM
# ──────────────────────────────────────────────────────────────────

def calculate_ground_floor(
    total_units: int,
    max_height_ft: float,
    bike_spaces: int = 0,
) -> GroundFloorProgram:
    """Calculate ground floor non-rentable program areas."""
    lobby = 300 if total_units < 30 else 500
    mailroom = 60
    package_room = 100 if total_units < 50 else 200
    super_office = 100
    electrical = 150
    fire_pump = 200 if max_height_ft > 75 else 0
    bike_storage = bike_spaces * 20  # 20 SF per bike space
    trash_collection = 300

    total = lobby + mailroom + package_room + super_office + electrical + fire_pump + bike_storage + trash_collection

    return GroundFloorProgram(
        lobby_sf=lobby,
        mailroom_sf=mailroom,
        package_room_sf=package_room,
        super_office_sf=super_office,
        electrical_meter_sf=electrical,
        fire_pump_room_sf=fire_pump,
        bike_storage_sf=bike_storage,
        trash_collection_sf=trash_collection,
        total_sf=total,
    )


# ──────────────────────────────────────────────────────────────────
# CELLAR PROGRAM
# ──────────────────────────────────────────────────────────────────

def calculate_cellar(
    total_units: int,
    has_cellar: bool = True,
    in_unit_laundry: bool = False,
) -> CellarProgram:
    """Calculate cellar/mechanical program areas."""
    if not has_cellar:
        return CellarProgram(
            boiler_room_sf=0,
            water_pump_room_sf=0,
            sprinkler_room_sf=0,
            resident_storage_sf=0,
            laundry_sf=0,
            total_sf=0,
        )

    boiler = 400
    water_pump = 200
    sprinkler = 150
    storage = total_units * 15  # 15 SF per unit code minimum

    # Laundry: 1 washer/dryer per 10 units if not in-unit
    if in_unit_laundry:
        laundry = 0
    else:
        machines = max(1, math.ceil(total_units / 10))
        laundry = 200 + machines * 20  # 200 base + 20 per machine

    total = boiler + water_pump + sprinkler + storage + laundry

    return CellarProgram(
        boiler_room_sf=boiler,
        water_pump_room_sf=water_pump,
        sprinkler_room_sf=sprinkler,
        resident_storage_sf=storage,
        laundry_sf=laundry,
        total_sf=total,
    )


# ──────────────────────────────────────────────────────────────────
# BULKHEAD / ROOF
# ──────────────────────────────────────────────────────────────────

def calculate_bulkhead(
    core: CoreSizing,
    num_floors: int,
) -> BulkheadProgram:
    """Calculate bulkhead and mechanical penthouse areas.

    These are permitted obstructions above the max building height
    per ZR 23-62, exempt from height limits.
    """
    stair_bulk = core.stairs * 150
    elev_bulk = (core.elevators + core.freight_elevators) * 100

    # Mechanical penthouse scales with building size
    if num_floors <= 6:
        mech = 300
    elif num_floors <= 15:
        mech = 400
    else:
        mech = 600

    total = stair_bulk + elev_bulk + mech

    return BulkheadProgram(
        stair_bulkhead_sf=stair_bulk,
        elevator_bulkhead_sf=elev_bulk,
        mechanical_penthouse_sf=mech,
        total_sf=total,
    )


# ──────────────────────────────────────────────────────────────────
# UNIT MIX
# ──────────────────────────────────────────────────────────────────

def generate_unit_mix(
    net_rentable_sf: float,
    strategy: str = "balanced",
    du_limit: int | None = None,
) -> UnitMixOption:
    """Generate a unit mix for a given strategy.

    Args:
        net_rentable_sf: Net rentable residential SF
        strategy: "maximize", "balanced", or "family"
        du_limit: Max dwelling units from DU factor (ZR 23-52)

    Returns UnitMixOption with unit breakdown.
    """
    if net_rentable_sf <= 0:
        return UnitMixOption(
            strategy=strategy,
            units=[],
            total_units=0,
            average_unit_sf=0,
            exceeds_du_limit=False,
            du_limit=du_limit,
        )

    pcts = UNIT_MIX_STRATEGIES.get(strategy, UNIT_MIX_STRATEGIES["balanced"])

    # Weighted average unit size for this strategy
    avg_size = sum(UNIT_SIZES[t] * pct for t, pct in pcts.items())
    total_units = max(1, round(net_rentable_sf / avg_size))

    # Check DU limit
    exceeds = False
    if du_limit is not None and total_units > du_limit:
        total_units = du_limit
        exceeds = True

    # Distribute units
    units = []
    allocated = 0
    unit_types = list(pcts.keys())
    for i, utype in enumerate(unit_types):
        if i == len(unit_types) - 1:
            count = total_units - allocated  # Last type gets remainder
        else:
            count = round(total_units * pcts[utype])
        count = max(0, count)
        allocated += count
        if count > 0:
            units.append({
                "type": utype,
                "count": count,
                "avg_sf": UNIT_SIZES[utype],
            })

    actual_total = sum(u["count"] for u in units)
    avg_unit = net_rentable_sf / actual_total if actual_total > 0 else 0

    return UnitMixOption(
        strategy=strategy,
        units=units,
        total_units=actual_total,
        average_unit_sf=round(avg_unit, 0),
        exceeds_du_limit=exceeds,
        du_limit=du_limit,
    )


def generate_all_unit_mixes(
    net_rentable_sf: float,
    du_limit: int | None = None,
) -> list[UnitMixOption]:
    """Generate unit mixes for all three strategies."""
    return [
        generate_unit_mix(net_rentable_sf, "maximize", du_limit),
        generate_unit_mix(net_rentable_sf, "balanced", du_limit),
        generate_unit_mix(net_rentable_sf, "family", du_limit),
    ]


# ──────────────────────────────────────────────────────────────────
# BUILDING CLASS
# ──────────────────────────────────────────────────────────────────

def get_building_class(num_floors: int) -> str:
    """Classify building by height for loss factor benchmarks."""
    if num_floors <= 6:
        return "walkup"
    if num_floors <= 12:
        return "midrise"
    if num_floors <= 24:
        return "highrise"
    return "tower"


# ──────────────────────────────────────────────────────────────────
# MAIN ENTRY: GENERATE BUILDING PROGRAM
# ──────────────────────────────────────────────────────────────────

def generate_building_program(
    scenario: dict,
    lot_depth: float = 100,
    lot_frontage: float = 50,
    borough: int = 0,
    community_district: int = 0,
    du_limit: int | None = None,
) -> BuildingProgram:
    """Generate a complete building program from a development scenario.

    Args:
        scenario: dict with keys from DevelopmentScenario — needs:
            total_gross_sf, zoning_floor_area, residential_sf,
            commercial_sf, cf_sf, total_units, num_floors,
            max_height_ft, floors (list of MassingFloor dicts)
        lot_depth: Lot depth in feet (for corridor calculation)
        lot_frontage: Lot frontage in feet
        borough: NYC borough code
        community_district: Community district number
        du_limit: Max DU from ZR 23-52 dwelling unit factor

    Returns BuildingProgram with full breakdown.
    """
    total_gross = scenario.get("total_gross_sf", 0)
    zfa = scenario.get("zoning_floor_area", 0)
    res_sf = scenario.get("residential_sf", 0)
    comm_sf = scenario.get("commercial_sf", 0)
    cf_sf = scenario.get("cf_sf", 0)
    total_units = scenario.get("total_units", 0)
    num_floors = scenario.get("num_floors", 0)
    max_height = scenario.get("max_height_ft", 0)
    floors = scenario.get("floors", [])

    # Typical floor footprint (average of residential floors)
    res_floors = [f for f in floors if f.get("use") == "residential"]
    if res_floors:
        typical_floor_sf = sum(f.get("gross_sf", 0) for f in res_floors) / len(res_floors)
    elif floors:
        typical_floor_sf = sum(f.get("gross_sf", 0) for f in floors) / len(floors)
    else:
        typical_floor_sf = total_gross / max(num_floors, 1)

    # Corridor type: double-loaded for narrow buildings (< 60 ft depth)
    effective_depth = lot_depth - 30  # Rough: subtract rear yard
    corridor_type = "double_loaded" if effective_depth >= 40 else "single_loaded"

    # ── Core ──
    core = calculate_core(
        num_floors=num_floors,
        total_units=total_units,
        typical_floor_sf=typical_floor_sf,
        building_depth=min(effective_depth, lot_depth),
        corridor_type=corridor_type,
    )
    total_core_area = core.total_core_sf_per_floor * num_floors

    # ── Ground floor ──
    # Bike parking from City of Yes
    bike = calculate_bicycle_parking(
        unit_count=total_units,
        commercial_sf=comm_sf,
        cf_sf=cf_sf,
    )
    ground_floor = calculate_ground_floor(
        total_units=total_units,
        max_height_ft=max_height,
        bike_spaces=bike.get("total_bike_spaces", 0),
    )

    # ── Cellar ──
    has_cellar = num_floors >= 3  # Most buildings 3+ floors have cellar
    cellar = calculate_cellar(
        total_units=total_units,
        has_cellar=has_cellar,
    )

    # ── Bulkhead ──
    bulkhead = calculate_bulkhead(core, num_floors)

    # ── Calculate net rentable areas ──
    # Gross above grade = total_gross (floors already exclude cellar)
    gross_above_grade = total_gross
    # Mechanical deductions = cellar + bulkhead (ZFA-exempt)
    mechanical_deductions = cellar.total_sf + bulkhead.total_sf

    # Net residential = gross residential - core allocation - ground floor deduction
    # Ground floor deduction only applies to the ground floor portion
    ground_floor_deduction = min(ground_floor.total_sf, typical_floor_sf)
    net_residential = max(0, res_sf - total_core_area * (res_sf / total_gross if total_gross > 0 else 0) - ground_floor_deduction)
    net_commercial = max(0, comm_sf * 0.93)  # Commercial typically 93% efficient

    # ── Loss factor ──
    total_net = net_residential + net_commercial
    total_with_cellar = gross_above_grade + cellar.total_sf
    loss_pct = ((total_with_cellar - total_net) / total_with_cellar * 100) if total_with_cellar > 0 else 0
    efficiency = total_net / total_with_cellar if total_with_cellar > 0 else 0

    # ── Unit mixes ──
    unit_mixes = generate_all_unit_mixes(net_residential, du_limit)

    bldg_class = get_building_class(num_floors)

    return BuildingProgram(
        gross_building_area=round(total_with_cellar),
        zoning_floor_area=round(zfa),
        mechanical_deductions=round(mechanical_deductions),
        gross_above_grade=round(gross_above_grade),
        core=core,
        ground_floor=ground_floor,
        cellar=cellar,
        bulkhead=bulkhead,
        total_core_area=round(total_core_area),
        net_rentable_residential=round(net_residential),
        net_rentable_commercial=round(net_commercial),
        loss_factor_pct=round(loss_pct, 1),
        efficiency_ratio=round(efficiency, 3),
        unit_mix_options=unit_mixes,
        num_floors=num_floors,
        max_height_ft=max_height,
        building_class=bldg_class,
    )
