"""
Parking layout engine.

Evaluates all physically feasible parking configurations for a development
scenario and ranks them by least impact on buildable area, then by cost.

Configurations evaluated:
  1. At-grade (surface lot)
  2. Below-grade (1 level underground)
  3. Below-grade (2 levels underground)
  4. Enclosed at-grade (ground floor of building)
  5. Mechanical stackers (double/triple)
  6. Ramp to 2nd floor

Each option reports: spaces provided, area consumed, impact on buildable,
estimated cost, and feasibility notes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class ParkingLayoutOption:
    """One evaluated parking configuration."""
    config_type: str
    spaces_provided: int
    meets_requirement: bool
    area_consumed_sf: float
    floors_consumed: list[str]
    impact_on_buildable: float  # SF of usable area lost from building program
    estimated_cost: float
    cost_per_space: float
    feasibility_notes: list[str]
    feasible: bool

    def to_dict(self) -> dict:
        return {
            "config_type": self.config_type,
            "spaces_provided": self.spaces_provided,
            "meets_requirement": self.meets_requirement,
            "area_consumed_sf": self.area_consumed_sf,
            "floors_consumed": self.floors_consumed,
            "impact_on_buildable": self.impact_on_buildable,
            "estimated_cost": self.estimated_cost,
            "cost_per_space": self.cost_per_space,
            "feasibility_notes": self.feasibility_notes,
            "feasible": self.feasible,
        }


@dataclass
class ParkingLayoutResult:
    """All evaluated parking configurations, ranked."""
    required_spaces: int
    options: list[ParkingLayoutOption]
    recommended: ParkingLayoutOption | None
    waiver_eligible: bool
    waiver_note: str

    def to_dict(self) -> dict:
        return {
            "required_spaces": self.required_spaces,
            "options": [o.to_dict() for o in self.options],
            "recommended": self.recommended.to_dict() if self.recommended else None,
            "waiver_eligible": self.waiver_eligible,
            "waiver_note": self.waiver_note,
        }


# ──────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────

SF_PER_SPACE_SURFACE = 350       # Including drive aisle
SF_PER_SPACE_STRUCTURED = 375    # Including ramp, columns, drive aisle
SF_PER_SPACE_STACKER_DOUBLE = 200
SF_PER_SPACE_STACKER_TRIPLE = 135

RAMP_SF_SINGLE_LANE = 720       # 12 ft wide × 60 ft long minimum
RAMP_SF_TWO_LEVEL = 1440        # Switchback or longer ramp for 2nd level
RAMP_SF_TO_SECOND_FLOOR = 1500  # Ground floor ramp structure

PARKING_FLOOR_HEIGHT = 10       # ft floor-to-floor
STACKER_DOUBLE_HEIGHT = 11.5    # ft minimum ceiling
STACKER_TRIPLE_HEIGHT = 18      # ft minimum ceiling

COST_SURFACE = 5000             # $ per space
COST_BELOW_GRADE_1 = 50000     # $ per space (1 level)
COST_BELOW_GRADE_2 = 70000     # $ per space (2nd level)
COST_ENCLOSED_GRADE = 30000    # $ per space
COST_STACKER = 30000           # $ per stacker unit
COST_RAMP_SECOND = 40000      # $ per space


# ──────────────────────────────────────────────────────────────────
# EVALUATION FUNCTIONS
# ──────────────────────────────────────────────────────────────────

def _evaluate_surface(
    required: int,
    lot_area: float,
    building_footprint: float,
) -> ParkingLayoutOption:
    """At-grade surface parking in remaining lot area."""
    available_area = max(0, lot_area - building_footprint)
    max_spaces = int(available_area / SF_PER_SPACE_SURFACE)
    spaces = min(required, max_spaces)
    area = spaces * SF_PER_SPACE_SURFACE
    cost = spaces * COST_SURFACE

    notes = []
    feasible = spaces > 0
    if spaces < required:
        notes.append(f"Only {spaces} of {required} spaces fit — lot too small for full surface parking.")
    if spaces > 10:
        notes.append("Surface parking >10 spaces is unusual for residential; consider structured.")
    if available_area < 500:
        notes.append("Very limited area available after building footprint.")
        feasible = False

    return ParkingLayoutOption(
        config_type="surface_lot",
        spaces_provided=spaces,
        meets_requirement=spaces >= required,
        area_consumed_sf=area,
        floors_consumed=["grade (open lot)"],
        impact_on_buildable=0,  # Surface lot doesn't consume building area
        estimated_cost=cost,
        cost_per_space=COST_SURFACE,
        feasibility_notes=notes,
        feasible=feasible,
    )


def _evaluate_below_grade_1(
    required: int,
    building_footprint: float,
) -> ParkingLayoutOption:
    """One level of underground parking."""
    # Usable area = footprint minus ramp, columns, mechanical
    usable = building_footprint - RAMP_SF_SINGLE_LANE - building_footprint * 0.08  # 8% columns/mechanical
    max_spaces = max(0, int(usable / SF_PER_SPACE_STRUCTURED))
    spaces = min(required, max_spaces)
    area = building_footprint  # Full cellar level consumed
    cost = spaces * COST_BELOW_GRADE_1

    notes = []
    feasible = spaces > 0 and building_footprint >= 800
    if spaces < required:
        notes.append(f"Only {spaces} of {required} spaces fit in one cellar level.")
    notes.append("Requires excavation; verify water table and rock conditions.")
    if building_footprint < 1500:
        notes.append("Small footprint may make below-grade parking uneconomical.")

    return ParkingLayoutOption(
        config_type="below_grade_1_level",
        spaces_provided=spaces,
        meets_requirement=spaces >= required,
        area_consumed_sf=area,
        floors_consumed=["cellar"],
        impact_on_buildable=area,  # Cellar used for parking instead of storage/mechanical
        estimated_cost=cost,
        cost_per_space=COST_BELOW_GRADE_1,
        feasibility_notes=notes,
        feasible=feasible,
    )


def _evaluate_below_grade_2(
    required: int,
    building_footprint: float,
) -> ParkingLayoutOption:
    """Two levels of underground parking."""
    usable_per_level = building_footprint - RAMP_SF_SINGLE_LANE - building_footprint * 0.08
    max_per_level = max(0, int(usable_per_level / SF_PER_SPACE_STRUCTURED))
    # Second level has longer ramp (switchback) eating more space
    usable_level_2 = building_footprint - RAMP_SF_TWO_LEVEL - building_footprint * 0.10
    max_level_2 = max(0, int(usable_level_2 / SF_PER_SPACE_STRUCTURED))
    max_spaces = max_per_level + max_level_2
    spaces = min(required, max_spaces)
    area = building_footprint * 2  # Both levels consumed
    # Cost: level 1 at standard, level 2 at premium
    level_1_spaces = min(spaces, max_per_level)
    level_2_spaces = max(0, spaces - level_1_spaces)
    cost = level_1_spaces * COST_BELOW_GRADE_1 + level_2_spaces * COST_BELOW_GRADE_2

    notes = []
    feasible = spaces > 0 and building_footprint >= 1200
    if spaces < required:
        notes.append(f"Only {spaces} of {required} spaces fit in two cellar levels.")
    notes.append("Two-level excavation: verify water table, rock, and adjacent foundations.")
    notes.append("Sub-cellar construction significantly increases structural costs.")
    if building_footprint < 2000:
        notes.append("Small footprint makes 2-level garage less practical.")

    avg_cost = cost / spaces if spaces > 0 else 0

    return ParkingLayoutOption(
        config_type="below_grade_2_levels",
        spaces_provided=spaces,
        meets_requirement=spaces >= required,
        area_consumed_sf=area,
        floors_consumed=["cellar", "sub-cellar"],
        impact_on_buildable=area,
        estimated_cost=cost,
        cost_per_space=round(avg_cost),
        feasibility_notes=notes,
        feasible=feasible,
    )


def _evaluate_enclosed_grade(
    required: int,
    building_footprint: float,
    is_quality_housing: bool = False,
) -> ParkingLayoutOption:
    """Enclosed parking on building's ground floor."""
    usable = building_footprint - RAMP_SF_SINGLE_LANE * 0.5  # Half ramp (just curb cut + internal)
    max_spaces = max(0, int(usable / SF_PER_SPACE_STRUCTURED))
    spaces = min(required, max_spaces)
    area = spaces * SF_PER_SPACE_STRUCTURED
    cost = spaces * COST_ENCLOSED_GRADE

    notes = []
    feasible = spaces > 0 and building_footprint >= 800
    notes.append("Ground floor parking reduces rentable area and active street frontage.")
    notes.append("Curb cut required — check DOT approval and street wall requirements.")
    if is_quality_housing:
        notes.append("QH district: street wall continuity rules may limit curb cut width.")
    if area > building_footprint * 0.6:
        notes.append("Parking consumes >60% of ground floor — consider wrapping with retail/lobby.")

    return ParkingLayoutOption(
        config_type="enclosed_at_grade",
        spaces_provided=spaces,
        meets_requirement=spaces >= required,
        area_consumed_sf=area,
        floors_consumed=["ground (partial)"],
        impact_on_buildable=area,  # Directly reduces ground floor program
        estimated_cost=cost,
        cost_per_space=COST_ENCLOSED_GRADE,
        feasibility_notes=notes,
        feasible=feasible,
    )


def _evaluate_stackers(
    required: int,
    building_footprint: float,
    ground_floor_height: float = 14,
) -> ParkingLayoutOption:
    """Mechanical car stackers (double or triple)."""
    # Determine stack type based on available height
    if ground_floor_height >= STACKER_TRIPLE_HEIGHT:
        stack_type = "triple"
        sf_per = SF_PER_SPACE_STACKER_TRIPLE
        stack_multiplier = 3
    elif ground_floor_height >= STACKER_DOUBLE_HEIGHT:
        stack_type = "double"
        sf_per = SF_PER_SPACE_STACKER_DOUBLE
        stack_multiplier = 2
    else:
        return ParkingLayoutOption(
            config_type="mechanical_stackers",
            spaces_provided=0,
            meets_requirement=False,
            area_consumed_sf=0,
            floors_consumed=[],
            impact_on_buildable=0,
            estimated_cost=0,
            cost_per_space=0,
            feasibility_notes=["Insufficient ceiling height for mechanical stackers."],
            feasible=False,
        )

    # Stacker footprint in cellar or ground floor
    # Each stacker unit: needs drive aisle in front
    drive_aisle = building_footprint * 0.25  # 25% for drive aisles
    usable = building_footprint - drive_aisle
    stacker_positions = max(0, int(usable / sf_per))
    spaces = min(required, stacker_positions * stack_multiplier)
    stacker_units = math.ceil(spaces / stack_multiplier) if spaces > 0 else 0
    area = stacker_units * sf_per + drive_aisle
    cost = stacker_units * COST_STACKER

    notes = []
    feasible = spaces > 0
    notes.append(f"{stack_type.title()}-stack configuration: {stack_multiplier}x vertical density.")
    notes.append(f"Retrieval time: 2-5 minutes per vehicle (slower than ramp garage).")
    notes.append(f"Requires dedicated operator or automated system.")
    if spaces < required:
        notes.append(f"Only {spaces} of {required} spaces fit with {stack_type} stackers.")

    return ParkingLayoutOption(
        config_type=f"mechanical_stackers_{stack_type}",
        spaces_provided=spaces,
        meets_requirement=spaces >= required,
        area_consumed_sf=round(area),
        floors_consumed=["cellar or ground (partial)"],
        impact_on_buildable=round(area),
        estimated_cost=cost,
        cost_per_space=round(cost / spaces) if spaces > 0 else 0,
        feasibility_notes=notes,
        feasible=feasible,
    )


def _evaluate_ramp_to_second(
    required: int,
    building_footprint: float,
    typical_floor_sf: float,
) -> ParkingLayoutOption:
    """Ramp from ground to 2nd floor parking."""
    # Ramp consumes ~1,500 SF of ground floor
    ramp_area = RAMP_SF_TO_SECOND_FLOOR
    if building_footprint < ramp_area * 1.5:
        return ParkingLayoutOption(
            config_type="ramp_to_2nd_floor",
            spaces_provided=0,
            meets_requirement=False,
            area_consumed_sf=0,
            floors_consumed=[],
            impact_on_buildable=0,
            estimated_cost=0,
            cost_per_space=0,
            feasibility_notes=["Building footprint too small for internal ramp."],
            feasible=False,
        )

    usable_2nd = typical_floor_sf - building_footprint * 0.08  # columns
    max_spaces = max(0, int(usable_2nd / SF_PER_SPACE_STRUCTURED))
    spaces = min(required, max_spaces)
    area = ramp_area + typical_floor_sf  # Ramp on ground + full 2nd floor
    cost = spaces * COST_RAMP_SECOND

    notes = []
    feasible = spaces > 0
    notes.append("Ramp to 2nd floor parking — unusual for residential, more common for commercial.")
    notes.append(f"Consumes full 2nd floor ({typical_floor_sf:,.0f} SF) + {ramp_area:,.0f} SF ramp on ground.")
    notes.append("Significant impact on building program — reduces residential floors by 1.")

    return ParkingLayoutOption(
        config_type="ramp_to_2nd_floor",
        spaces_provided=spaces,
        meets_requirement=spaces >= required,
        area_consumed_sf=round(area),
        floors_consumed=["ground (ramp)", "2nd floor"],
        impact_on_buildable=round(area),
        estimated_cost=cost,
        cost_per_space=COST_RAMP_SECOND,
        feasibility_notes=notes,
        feasible=feasible,
    )


# ──────────────────────────────────────────────────────────────────
# MAIN ENTRY
# ──────────────────────────────────────────────────────────────────

def evaluate_parking_layouts(
    required_spaces: int,
    lot_area: float,
    building_footprint: float,
    typical_floor_sf: float = 0,
    lot_frontage: float = 50,
    lot_depth: float = 100,
    ground_floor_height: float = 14,
    is_quality_housing: bool = False,
    waiver_eligible: bool = False,
) -> ParkingLayoutResult:
    """Evaluate all feasible parking configurations for a site.

    Args:
        required_spaces: Required automobile parking spaces
        lot_area: Total lot area in SF
        building_footprint: Building footprint (ground floor) in SF
        typical_floor_sf: Typical upper floor gross SF
        lot_frontage: Lot frontage in feet
        lot_depth: Lot depth in feet
        ground_floor_height: Ground floor height in feet
        is_quality_housing: Whether QH street wall rules apply
        waiver_eligible: Whether parking waiver is available

    Returns ParkingLayoutResult with all options ranked.
    """
    if typical_floor_sf <= 0:
        typical_floor_sf = building_footprint

    waiver_note = ""
    if required_spaces == 0:
        waiver_note = "No parking required (transit zone or small building waiver)."
        return ParkingLayoutResult(
            required_spaces=0,
            options=[],
            recommended=None,
            waiver_eligible=True,
            waiver_note=waiver_note,
        )

    if waiver_eligible:
        waiver_note = "Parking waiver available — consider building without parking to maximize usable area."

    # Evaluate all configurations
    options = [
        _evaluate_surface(required_spaces, lot_area, building_footprint),
        _evaluate_below_grade_1(required_spaces, building_footprint),
        _evaluate_below_grade_2(required_spaces, building_footprint),
        _evaluate_enclosed_grade(required_spaces, building_footprint, is_quality_housing),
        _evaluate_stackers(required_spaces, building_footprint, ground_floor_height),
        _evaluate_ramp_to_second(required_spaces, building_footprint, typical_floor_sf),
    ]

    # Filter to feasible options
    feasible = [o for o in options if o.feasible]

    # Rank: feasible first, then by least impact on buildable, then by cost
    feasible.sort(key=lambda o: (
        0 if o.meets_requirement else 1,
        o.impact_on_buildable,
        o.estimated_cost,
    ))

    # Recommend the best feasible option that meets the requirement
    recommended = None
    for o in feasible:
        if o.meets_requirement:
            recommended = o
            break
    if recommended is None and feasible:
        recommended = feasible[0]

    return ParkingLayoutResult(
        required_spaces=required_spaces,
        options=options,
        recommended=recommended,
        waiver_eligible=waiver_eligible,
        waiver_note=waiver_note,
    )
