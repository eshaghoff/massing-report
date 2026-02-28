"""
NYC Zoning Resolution Court Regulations (ZR 23-84, 23-85, 23-86).

Courts are open areas within or at the edges of buildings that provide
light and air to legally required windows. The regulations constrain
the achievable floor plate size, especially on mid-block (interior) lots.

Key rules:
- Inner courts (ZR 23-85): open areas enclosed on all sides by building walls
  At/below 75ft: min 800 SF, min 20ft dimension
  Above 75ft:    min 1,200 SF, min 30ft dimension

- Outer courts (ZR 23-84): open from one side (facing lot line or street)
  Width must be >= depth; unlimited depth if width > 20ft (<=75ft) or 30ft (>75ft)

- Min distance from window to wall/lot line (ZR 23-86): 20ft general,
  15ft in R3-R5 to side lot line, 10ft min to rear lot line
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class CourtRequirements:
    """Court requirements for a given building configuration."""
    needs_inner_court: bool = False
    inner_court_min_area: float = 0     # SF
    inner_court_min_dim: float = 0      # ft
    min_window_distance: float = 20.0   # ft from window to wall/lot line
    court_area_deduction: float = 0     # SF per floor deducted from plate
    effective_footprint: float = 0      # Adjusted footprint after court deduction
    notes: list[str] = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []


# Max depth of a wing before a court is needed for light/air.
# NYC Multiple Dwelling Law requires legally required windows within
# 30ft of an exterior wall or court. Practical rule: if building depth
# exceeds ~60ft, you need a court or notch for window compliance.
MAX_WING_DEPTH = 30.0  # ft — max distance from window to exterior wall


def calculate_court_requirements(
    lot_depth: float,
    lot_width: float,
    lot_type: str,
    building_height: float,
    footprint: float,
    district: str = "",
    rear_yard: float = 30.0,
    front_yard: float = 0.0,
    side_yards: float = 0.0,
) -> CourtRequirements:
    """Calculate court requirements and effective footprint deduction.

    Determines whether the building needs light courts based on lot
    dimensions and calculates the area deducted from the floor plate.

    Args:
        lot_depth: Lot depth in feet
        lot_width: Lot width / frontage in feet
        lot_type: "interior", "corner", or "through"
        building_height: Max building height in feet
        footprint: Gross building footprint before court deduction (SF)
        district: Zoning district
        rear_yard: Required rear yard depth (ft)
        front_yard: Required front yard depth (ft)
        side_yards: Total side yard width (both sides combined, ft)

    Returns:
        CourtRequirements with deduction calculations
    """
    result = CourtRequirements()
    result.notes = []

    # ── Determine buildable depth ──
    if lot_type == "through":
        # Through lots: rear yard equivalent applies (ZR 23-532/533)
        # Typically 60ft open area mid-lot, leaving two buildable wings
        buildable_depth = (lot_depth - 60.0) / 2.0 if lot_depth > 60 else lot_depth
        result.notes.append(
            f"Through lot: 60ft rear yard equivalent mid-block, "
            f"two wings of {buildable_depth:.0f}ft each"
        )
    else:
        buildable_depth = lot_depth - rear_yard - front_yard

    buildable_width = lot_width - side_yards

    if buildable_depth <= 0 or buildable_width <= 0:
        result.effective_footprint = footprint
        return result

    # ── Determine court height threshold ──
    is_tall = building_height > 75

    if is_tall:
        result.inner_court_min_area = 1200  # SF
        result.inner_court_min_dim = 30     # ft
        result.min_window_distance = 20     # ft
    else:
        result.inner_court_min_area = 800   # SF
        result.inner_court_min_dim = 20     # ft
        result.min_window_distance = 20     # ft

    # R3-R5 have reduced side-to-window distance
    dist_upper = district.strip().upper()
    if any(dist_upper.startswith(d) for d in ("R3", "R4", "R5")):
        result.min_window_distance = 15  # ft to side lot line

    # ── Does the building need a court? ──
    # A court is needed when the building depth exceeds 2 × MAX_WING_DEPTH
    # (i.e., windows on both sides can't reach the center of the floor plate).
    # For interior lots: light comes from front and rear only (sides are lot lines).
    # For corner lots: light comes from front, side street, and rear.

    if lot_type == "interior":
        # Interior lot: windows face front and rear only (no side windows).
        # If buildable depth > 2 × 30ft = 60ft, center needs a court.
        needs_court = buildable_depth > (2 * MAX_WING_DEPTH)
        # Also check width: if wider than 2 × window distance, side edges
        # need courts too (but usually side lot lines block windows anyway)
    elif lot_type == "corner":
        # Corner lot: windows can face front, side street, and rear.
        # Much more flexibility — courts rarely needed unless very deep.
        needs_court = buildable_depth > (2 * MAX_WING_DEPTH + 10)
    elif lot_type == "through":
        # Through lot: each wing already has front and "court" exposure
        needs_court = buildable_depth > (2 * MAX_WING_DEPTH)
    else:
        needs_court = buildable_depth > (2 * MAX_WING_DEPTH)

    if not needs_court:
        result.effective_footprint = footprint
        result.notes.append(
            f"No court needed: buildable depth {buildable_depth:.0f}ft "
            f"<= {2 * MAX_WING_DEPTH:.0f}ft (2 × {MAX_WING_DEPTH:.0f}ft wing depth)"
        )
        return result

    # ── Calculate court deduction ──
    result.needs_inner_court = True

    # The court must be large enough to satisfy the minimum area and dimension.
    # Typical layout: a rectangular court running perpendicular to the street.
    court_dim = result.inner_court_min_dim  # width of court
    excess_depth = buildable_depth - (2 * MAX_WING_DEPTH)

    # Court depth = excess beyond two wings, but at least min dimension
    court_depth = max(excess_depth, court_dim)
    # Court width = at least min dimension
    court_width = court_dim

    court_area = court_depth * court_width
    # Ensure minimum area is met
    if court_area < result.inner_court_min_area:
        court_area = result.inner_court_min_area
        # Recalculate dimensions to meet min area
        court_width = max(court_dim, result.inner_court_min_area / court_depth)
        court_area = court_depth * court_width

    result.court_area_deduction = round(court_area)
    result.effective_footprint = max(0, footprint - court_area)

    result.notes.append(
        f"Inner court required: buildable depth {buildable_depth:.0f}ft "
        f"exceeds 2 × {MAX_WING_DEPTH:.0f}ft. "
        f"Court: {court_width:.0f}ft × {court_depth:.0f}ft = {court_area:,.0f} SF. "
        f"Effective footprint: {result.effective_footprint:,.0f} SF "
        f"(was {footprint:,.0f} SF)"
    )

    return result
