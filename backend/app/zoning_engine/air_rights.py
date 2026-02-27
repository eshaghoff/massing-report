"""
Air Rights Calculator for NYC Zoning Lot Mergers.

When multiple lots are merged into a single zoning lot and one or more
lots elect to keep their existing building, the remaining development
potential (unused floor area) can be transferred to the receiving lot(s).

Per NYC Zoning Resolution:
  - Total development potential = merged_lot_area × applicable FAR
  - Existing building area on "kept" lots counts against total ZFA
  - Remaining ZFA can be built on the development (receiving) lot(s)
  - Physical constraints (height, setback) apply to the development site
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.models.schemas import LotProfile, ZoningEnvelope


@dataclass
class AirRightsResult:
    """Result of air rights / floor area transfer calculation."""

    # Combined site
    total_lot_area: float          # All lots combined (sq ft)
    total_allowable_zfa: float     # merged_area × applicable FAR
    applicable_far: float          # FAR used for calculation

    # Deductions
    existing_kept_area: float      # Sum of bldgarea for kept lots
    developable_zfa: float         # total_allowable - existing_kept

    # Development site (non-kept lots)
    development_lot_area: float    # Area of lots NOT keeping buildings
    development_lot_count: int

    # Detail per lot
    kept_lots: list[dict] = field(default_factory=list)
    development_lots: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_lot_area": self.total_lot_area,
            "total_allowable_zfa": round(self.total_allowable_zfa, 0),
            "applicable_far": self.applicable_far,
            "existing_kept_area": self.existing_kept_area,
            "developable_zfa": round(self.developable_zfa, 0),
            "development_lot_area": self.development_lot_area,
            "development_lot_count": self.development_lot_count,
            "kept_lots": self.kept_lots,
            "development_lots": self.development_lots,
        }


def calculate_air_rights(
    lots: list[LotProfile],
    keep_flags: list[bool],
    envelope: ZoningEnvelope,
    merged_lot_area: float,
) -> AirRightsResult:
    """Calculate developable ZFA after subtracting kept building areas.

    Args:
        lots: Individual lot profiles (with PLUTO data).
        keep_flags: Parallel list — True = keep existing building on that lot.
        envelope: Zoning envelope for the merged lot.
        merged_lot_area: Total merged lot area (sq ft).

    Returns:
        AirRightsResult with breakdown of transferable floor area.
    """
    # Applicable FAR = max of residential and commercial (excludes CF)
    applicable_far = max(
        envelope.residential_far or 0,
        envelope.commercial_far or 0,
    )
    total_allowable_zfa = merged_lot_area * applicable_far

    # Tally existing building area on kept lots
    kept_lots = []
    development_lots = []
    existing_kept_area = 0.0
    development_lot_area = 0.0

    for lot, keep in zip(lots, keep_flags):
        bldgarea = (lot.pluto.bldgarea if lot.pluto else 0) or 0
        lot_area = lot.lot_area or 0
        lot_far = lot.pluto.builtfar if lot.pluto else 0
        lot_far = lot_far or 0

        lot_info = {
            "bbl": lot.bbl,
            "address": lot.address or "",
            "lot_area": lot_area,
            "bldgarea": bldgarea,
            "builtfar": lot_far,
            "numfloors": (lot.pluto.numfloors if lot.pluto else 0) or 0,
            "yearbuilt": (lot.pluto.yearbuilt if lot.pluto else 0) or 0,
        }

        if keep:
            existing_kept_area += bldgarea
            lot_info["unused_far"] = round(applicable_far - lot_far, 2)
            lot_info["unused_zfa"] = round(
                lot_area * applicable_far - bldgarea, 0
            )
            kept_lots.append(lot_info)
        else:
            development_lot_area += lot_area
            development_lots.append(lot_info)

    developable_zfa = max(0.0, total_allowable_zfa - existing_kept_area)

    return AirRightsResult(
        total_lot_area=merged_lot_area,
        total_allowable_zfa=total_allowable_zfa,
        applicable_far=applicable_far,
        existing_kept_area=existing_kept_area,
        developable_zfa=developable_zfa,
        development_lot_area=development_lot_area,
        development_lot_count=len(development_lots),
        kept_lots=kept_lots,
        development_lots=development_lots,
    )


def adjust_scenarios_for_air_rights(
    scenarios: list,
    air_rights: AirRightsResult,
) -> list:
    """Adjust scenario ZFA/units to reflect air rights deduction.

    When existing buildings are kept, each scenario's ZFA is capped
    at the developable_zfa. Units and SF are scaled proportionally.
    """
    if air_rights.developable_zfa <= 0:
        return scenarios

    for scenario in scenarios:
        original_zfa = scenario.zoning_floor_area or scenario.total_gross_sf or 0
        if original_zfa <= 0:
            continue

        if original_zfa > air_rights.developable_zfa:
            ratio = air_rights.developable_zfa / original_zfa
            scenario.zoning_floor_area = round(air_rights.developable_zfa, 0)
            scenario.total_gross_sf = round(
                (scenario.total_gross_sf or 0) * ratio, 0
            )
            scenario.total_net_sf = round(
                (scenario.total_net_sf or 0) * ratio, 0
            )
            if scenario.total_units:
                scenario.total_units = max(1, round(scenario.total_units * ratio))
            if scenario.residential_sf:
                scenario.residential_sf = round(scenario.residential_sf * ratio, 0)
            if scenario.commercial_sf:
                scenario.commercial_sf = round(scenario.commercial_sf * ratio, 0)
            if scenario.cf_sf:
                scenario.cf_sf = round(scenario.cf_sf * ratio, 0)
            # Update FAR used
            if air_rights.total_lot_area > 0:
                scenario.far_used = round(
                    air_rights.developable_zfa / air_rights.total_lot_area, 2
                )

    return scenarios
