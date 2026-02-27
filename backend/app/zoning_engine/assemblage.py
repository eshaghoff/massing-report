"""
NYC Zoning Assemblage Engine.

Analyzes the value of assembling multiple contiguous lots into a single
development site by comparing individual vs merged development capacity.

Pipeline:
  1. Input: list of 2+ BBLs or addresses
  2. Resolve each lot: geocode → PLUTO → geometry
  3. Validate contiguity (shared boundary or same-block adjacency)
  4. Run individual analyses (baseline)
  5. Merge lots (union polygons, recalculate dimensions)
  6. Run merged analysis
  7. Calculate deltas per scenario
  8. Flag key unlocks (through lot, corner lot, side yard elimination, etc.)

Key assemblage nuances:
  - Side yard elimination: assembling interior lots removes side lot lines,
    eliminating side yards between them → more buildable footprint.
  - Through lot rear yard: ZR §23-532/533 — rear yard equivalent is more
    flexible than standard 30 ft rear yard.
  - Split-zoned assemblage: lots in different districts → flag averaging
    opportunity per ZR §77-02/03.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Optional

from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import unary_union

from app.models.schemas import (
    LotProfile, ZoningEnvelope, DevelopmentScenario, PlutoData,
)
from app.zoning_engine.calculator import ZoningCalculator


# ──────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────

@dataclass
class ScenarioDelta:
    """Delta between merged and individual scenarios."""
    scenario_name: str
    far_delta: float = 0
    zfa_delta: float = 0
    height_delta: float = 0
    unit_count_delta: int = 0
    parking_delta: int = 0
    loss_factor_delta: float = 0
    additional_buildable_sf: float = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AssemblageDelta:
    """Summary of changes from assembling lots."""
    lot_area_change: float = 0
    lot_type_change: Optional[str] = None
    street_frontage_change: dict = field(default_factory=dict)
    footprint_gain_sf: float = 0
    scenario_deltas: list[ScenarioDelta] = field(default_factory=list)
    key_unlocks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["scenario_deltas"] = [sd.to_dict() for sd in self.scenario_deltas]
        return d


@dataclass
class AssemblageAnalysis:
    """Complete assemblage analysis result."""
    individual_lots: list[LotProfile]
    individual_analyses: list[dict]  # Full calc result per lot
    merged_lot: LotProfile
    merged_analysis: dict  # Full calc result for merged
    delta: AssemblageDelta
    contiguity_validated: bool = True
    contiguity_method: str = "geometry"  # "geometry" or "block_adjacency"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "individual_lots": [l.dict() for l in self.individual_lots],
            "individual_analyses": [
                _serialize_analysis(a) for a in self.individual_analyses
            ],
            "merged_lot": self.merged_lot.dict(),
            "merged_analysis": _serialize_analysis(self.merged_analysis),
            "delta": self.delta.to_dict(),
            "contiguity_validated": self.contiguity_validated,
            "contiguity_method": self.contiguity_method,
            "warnings": self.warnings,
        }


def _serialize_analysis(analysis: dict) -> dict:
    """Convert a calculator result to a serializable dict."""
    result = {}
    for k, v in analysis.items():
        if k == "zoning_envelope":
            result[k] = v.dict() if hasattr(v, "dict") else v
        elif k == "scenarios":
            result[k] = [s.dict() if hasattr(s, "dict") else s for s in v]
        else:
            result[k] = v
    return result


# ──────────────────────────────────────────────────────────────────
# MAIN ANALYSIS FUNCTION
# ──────────────────────────────────────────────────────────────────

def analyze_assemblage(
    lots: list[LotProfile],
    calculator: Optional[ZoningCalculator] = None,
) -> AssemblageAnalysis:
    """Analyze the development value of assembling lots.

    Args:
        lots: List of 2+ LotProfiles with geometry and PLUTO data
        calculator: Optional ZoningCalculator instance (will create if not provided)

    Returns:
        AssemblageAnalysis with individual analyses, merged analysis, and deltas.

    Raises:
        ValueError: If fewer than 2 lots or lots are not contiguous.
    """
    if len(lots) < 2:
        raise ValueError("Assemblage requires at least 2 lots.")

    calc = calculator or ZoningCalculator()
    warnings = []

    # Step 1: Validate contiguity
    contiguity_ok, contiguity_method, contiguity_msg = validate_contiguity(lots)
    if not contiguity_ok:
        raise ValueError(contiguity_msg)

    # Step 2: Run individual analyses
    individual_analyses = []
    for lot in lots:
        try:
            result = calc.calculate(lot)
            individual_analyses.append(result)
        except Exception as e:
            warnings.append(f"Error analyzing lot {lot.bbl}: {e}")
            individual_analyses.append({"zoning_envelope": None, "scenarios": []})

    # Step 3: Merge lots
    merged_lot, merge_warnings = merge_lots(lots)
    warnings.extend(merge_warnings)

    # Step 4: Run merged analysis
    try:
        merged_analysis = calc.calculate(merged_lot)
    except Exception as e:
        warnings.append(f"Error analyzing merged lot: {e}")
        merged_analysis = {"zoning_envelope": None, "scenarios": []}

    # Step 5: Calculate deltas
    delta = calculate_delta(lots, individual_analyses, merged_lot, merged_analysis)

    # Step 6: Flag key unlocks
    delta.key_unlocks = identify_key_unlocks(lots, merged_lot, delta)

    return AssemblageAnalysis(
        individual_lots=lots,
        individual_analyses=individual_analyses,
        merged_lot=merged_lot,
        merged_analysis=merged_analysis,
        delta=delta,
        contiguity_validated=contiguity_ok,
        contiguity_method=contiguity_method,
        warnings=warnings,
    )


# ──────────────────────────────────────────────────────────────────
# CONTIGUITY VALIDATION
# ──────────────────────────────────────────────────────────────────

def validate_contiguity(
    lots: list[LotProfile],
) -> tuple[bool, str, str]:
    """Validate that lots are contiguous (share boundaries).

    Returns (is_valid, method, error_message).
    Method is "geometry" if using polygon .touches()/.intersects(),
    or "block_adjacency" as fallback.
    """
    # Try geometry-based validation first
    polygons = []
    has_geometry = True
    for lot in lots:
        if lot.geometry:
            try:
                poly = shape(lot.geometry)
                if isinstance(poly, MultiPolygon):
                    poly = max(poly.geoms, key=lambda p: p.area)
                polygons.append((lot.bbl, poly))
            except Exception:
                has_geometry = False
                break
        else:
            has_geometry = False
            break

    if has_geometry and len(polygons) == len(lots):
        return _validate_geometry_contiguity(polygons)

    # Fallback: block adjacency
    return _validate_block_adjacency(lots)


def _measure_shared_boundary_ft(p1: Polygon, p2: Polygon) -> float:
    """Measure shared boundary length between two polygons in feet.

    Polygons are in WGS84 (EPSG:4326). We transform to NY State Plane
    Long Island (EPSG:2263, units in feet) for accurate measurement.
    """
    try:
        from pyproj import Transformer
        from shapely.ops import transform as shp_transform

        transformer = Transformer.from_crs(
            "EPSG:4326", "EPSG:2263", always_xy=True
        )
        p1_ft = shp_transform(transformer.transform, p1)
        p2_ft = shp_transform(transformer.transform, p2)
        shared = p1_ft.boundary.intersection(p2_ft.boundary)
        return shared.length
    except ImportError:
        # Fallback: approximate using NYC latitude
        # At 40.7°N: 1° longitude ≈ 84,400 m, 1° latitude ≈ 111,320 m
        shared = p1.boundary.intersection(p2.boundary)
        # Average conversion at NYC: degrees to feet
        avg_m_per_deg = (84_400 + 111_320) / 2
        return shared.length * avg_m_per_deg * 3.28084  # meters → feet


def _validate_geometry_contiguity(
    polygons: list[tuple[str, Polygon]],
    min_boundary_ft: float = 10.0,
) -> tuple[bool, str, str]:
    """Check contiguity AND enforce minimum shared boundary per ZR §12-10.

    Per NYC Zoning Resolution Section 12-10, lots must share a common
    boundary of at least 10 linear feet to qualify for zoning lot merger.

    Uses a graph approach: each lot must be reachable from every other
    lot through qualifying (≥ min_boundary_ft) shared boundaries.
    """
    n = len(polygons)
    # Build adjacency graph with boundary length enforcement
    adj = {i: set() for i in range(n)}
    boundary_lengths = {}  # (i, j) → feet

    for i in range(n):
        for j in range(i + 1, n):
            p1 = polygons[i][1]
            p2 = polygons[j][1]

            # Check intersection first (fast)
            if not p1.buffer(0.5).intersects(p2.buffer(0.5)):
                continue

            # Measure shared boundary in feet
            shared_ft = _measure_shared_boundary_ft(p1, p2)
            boundary_lengths[(i, j)] = shared_ft

            if shared_ft >= min_boundary_ft:
                adj[i].add(j)
                adj[j].add(i)

    # BFS from lot 0 to check all lots are reachable
    visited = set()
    queue = [0]
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        for neighbor in adj[node]:
            if neighbor not in visited:
                queue.append(neighbor)

    if len(visited) == n:
        return True, "geometry", ""

    # Find which lots are disconnected
    disconnected = set(range(n)) - visited
    disconnected_bbls = [polygons[i][0] for i in disconnected]

    # Check if they touch but fail the 10ft requirement
    short_boundaries = []
    for (i, j), ft in boundary_lengths.items():
        if ft < min_boundary_ft:
            short_boundaries.append(
                f"{polygons[i][0]} ↔ {polygons[j][0]}: {ft:.1f} ft"
            )

    detail = (
        f"Lots are not contiguous. BBL(s) {', '.join(disconnected_bbls)} "
        f"do not share a qualifying boundary (≥{min_boundary_ft} ft) "
        f"with any other lot in the set."
    )
    if short_boundaries:
        detail += (
            f" Insufficient shared boundaries found: "
            + "; ".join(short_boundaries)
        )

    return (
        False,
        "geometry",
        detail,
    )


def _validate_block_adjacency(
    lots: list[LotProfile],
) -> tuple[bool, str, str]:
    """Fallback: check if lots share the same block and have adjacent lot numbers."""
    # Group by block
    blocks = {}
    for lot in lots:
        blocks.setdefault(lot.block, []).append(lot)

    if len(blocks) > 2:
        return (
            False,
            "block_adjacency",
            "Lots span more than 2 blocks — likely not contiguous.",
        )

    # Within each block, check lot number adjacency
    for block_num, block_lots in blocks.items():
        lot_nums = sorted([l.lot for l in block_lots])
        for i in range(len(lot_nums) - 1):
            gap = lot_nums[i + 1] - lot_nums[i]
            # Lot numbers are usually sequential or close (within 5)
            if gap > 10:
                return (
                    False,
                    "block_adjacency",
                    f"Lot numbers on block {block_num} are not adjacent "
                    f"(gap of {gap} between lots {lot_nums[i]} and {lot_nums[i+1]}). "
                    f"Lots may not be contiguous.",
                )

    return (
        True,
        "block_adjacency",
        "",
    )


# ──────────────────────────────────────────────────────────────────
# LOT MERGING
# ──────────────────────────────────────────────────────────────────

def merge_lots(lots: list[LotProfile]) -> tuple[LotProfile, list[str]]:
    """Merge multiple lots into a single development site.

    Computes merged geometry, dimensions, lot type, and zoning districts.

    Returns (merged_lot, warnings).
    """
    warnings = []

    # Merge geometry
    merged_geom, geom_warnings = _merge_geometry(lots)
    warnings.extend(geom_warnings)

    # Calculate merged dimensions
    merged_area = sum(l.lot_area or 0 for l in lots)
    merged_frontage = sum(l.lot_frontage or 0 for l in lots)
    merged_depth = max((l.lot_depth or 0) for l in lots) if lots else 100

    # Use polygon-based dimensions if available
    if merged_geom:
        try:
            poly = shape(merged_geom)
            if isinstance(poly, MultiPolygon):
                poly = max(poly.geoms, key=lambda p: p.area)
            # More accurate area from polygon
            # (Keep PLUTO sum as primary — polygon area is in degrees²)
            merged_frontage, merged_depth = _measure_polygon_dimensions(poly, lots)
        except Exception:
            pass

    # Determine lot type for merged lot
    merged_lot_type = _determine_merged_lot_type(lots, merged_geom)

    # Collect zoning districts, overlays, special districts
    zoning_districts = _collect_unique_ordered([
        d for l in lots for d in l.zoning_districts
    ])
    overlays = _collect_unique_ordered([
        o for l in lots for o in l.overlays
    ])
    special_districts = _collect_unique_ordered([
        s for l in lots for s in l.special_districts
    ])

    # Check for split-zoning
    unique_districts = list(set(zoning_districts))
    is_split = len(unique_districts) > 1
    if is_split:
        warnings.append(
            f"Merged lot spans multiple zoning districts: {', '.join(unique_districts)}. "
            f"Split-zone rules (ZR §77-02/03) may allow FAR averaging."
        )

    # Use first lot's borough and block; generate a pseudo-BBL for the merged lot
    first = lots[0]
    merged_bbl = f"{first.bbl[:6]}9999"  # Use lot 9999 as pseudo-merged

    # Street width: use widest
    street_width = "narrow"
    if any(l.street_width == "wide" for l in lots):
        street_width = "wide"

    # Build merged PLUTO data (aggregate)
    merged_pluto = PlutoData(
        bbl=merged_bbl,
        address=f"Assemblage: {', '.join(l.bbl for l in lots)}",
        zonedist1=zoning_districts[0] if zoning_districts else None,
        zonedist2=zoning_districts[1] if len(zoning_districts) > 1 else None,
        lotarea=merged_area,
        lotfront=merged_frontage,
        lotdepth=merged_depth,
        cd=first.pluto.cd if first.pluto else None,
    )

    merged_lot = LotProfile(
        bbl=merged_bbl,
        address=f"Assembled: {len(lots)} lots",
        borough=first.borough,
        block=first.block,
        lot=9999,
        latitude=first.latitude,
        longitude=first.longitude,
        pluto=merged_pluto,
        geometry=merged_geom,
        zoning_districts=zoning_districts,
        overlays=overlays,
        special_districts=special_districts,
        split_zone=is_split,
        lot_area=merged_area,
        lot_frontage=merged_frontage,
        lot_depth=merged_depth,
        lot_type=merged_lot_type,
        street_width=street_width,
        is_mih_area=any(l.is_mih_area for l in lots),
        mih_option=next((l.mih_option for l in lots if l.mih_option), None),
    )

    return merged_lot, warnings


def _merge_geometry(lots: list[LotProfile]) -> tuple[Optional[dict], list[str]]:
    """Merge lot geometries using Shapely unary_union.

    Returns (merged_geojson, warnings).
    """
    warnings = []
    polys = []

    for lot in lots:
        if lot.geometry:
            try:
                poly = shape(lot.geometry)
                if isinstance(poly, MultiPolygon):
                    poly = max(poly.geoms, key=lambda p: p.area)
                polys.append(poly)
            except Exception:
                warnings.append(f"Could not parse geometry for BBL {lot.bbl}")

    if not polys:
        warnings.append("No lot geometries available — using dimensional estimates.")
        return None, warnings

    if len(polys) < len(lots):
        warnings.append(
            f"Geometry available for only {len(polys)} of {len(lots)} lots. "
            f"Merged geometry may be incomplete."
        )

    merged = unary_union(polys)
    if isinstance(merged, MultiPolygon):
        # If union results in disconnected pieces, take the largest
        merged = max(merged.geoms, key=lambda p: p.area)
        warnings.append(
            "Lot geometries did not form a single polygon. "
            "Using largest contiguous piece."
        )

    import json
    return json.loads(json.dumps(merged.__geo_interface__)), warnings


def _measure_polygon_dimensions(
    poly: Polygon, lots: list[LotProfile],
) -> tuple[float, float]:
    """Measure frontage and depth from merged polygon.

    Frontage = longest continuous street edge.
    Depth = perpendicular distance from front to rear.

    Falls back to PLUTO-based sum if polygon measurement fails.
    """
    try:
        # Use minimum rotated rectangle for regular approximation
        min_rect = poly.minimum_rotated_rectangle
        coords = list(min_rect.exterior.coords)

        # Measure the two edge lengths of the rectangle
        edge1 = math.sqrt(
            (coords[1][0] - coords[0][0]) ** 2 +
            (coords[1][1] - coords[0][1]) ** 2
        )
        edge2 = math.sqrt(
            (coords[2][0] - coords[1][0]) ** 2 +
            (coords[2][1] - coords[1][1]) ** 2
        )

        # In NYC, frontage is typically the shorter dimension for interior lots
        # and the longer dimension for wide lots. Use PLUTO heuristic.
        pluto_frontage = sum(l.lot_frontage or 0 for l in lots)
        pluto_depth = max((l.lot_depth or 0) for l in lots)

        # The dimension closer to the PLUTO sum-of-frontages is the frontage
        if abs(edge1 - pluto_frontage) < abs(edge2 - pluto_frontage):
            return pluto_frontage, pluto_depth
        else:
            return pluto_frontage, pluto_depth
    except Exception:
        return (
            sum(l.lot_frontage or 0 for l in lots),
            max((l.lot_depth or 0) for l in lots),
        )


def _determine_merged_lot_type(
    lots: list[LotProfile],
    merged_geom: Optional[dict],
) -> str:
    """Determine the lot type of the merged site.

    Key scenarios:
      - Two interior lots on same street → still interior (but wider)
      - Interior + corner lot → corner
      - Lots on parallel streets → through lot (big unlock!)
      - Lots on perpendicular streets → corner
    """
    lot_types = [l.lot_type for l in lots]

    # If any lot is a corner lot, merged is corner
    if "corner" in lot_types:
        return "corner"

    # Check for through lot: lots with different street addresses
    # that suggest parallel streets
    streets = set()
    for lot in lots:
        if lot.pluto and lot.pluto.address:
            # Extract street name from address
            parts = lot.pluto.address.strip().split(" ", 1)
            if len(parts) == 2:
                streets.add(parts[1].upper())

    if len(streets) >= 2:
        # Different streets — could be through lot or corner
        # Without detailed street geometry, assume through lot if lots
        # are on same block with different streets
        blocks = set(l.block for l in lots)
        if len(blocks) == 1:
            return "through"
        return "corner"

    # Default: interior (wider than individual lots)
    return "interior"


def _collect_unique_ordered(items: list) -> list:
    """Collect unique items preserving insertion order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


# ──────────────────────────────────────────────────────────────────
# DELTA CALCULATION
# ──────────────────────────────────────────────────────────────────

def calculate_delta(
    lots: list[LotProfile],
    individual_analyses: list[dict],
    merged_lot: LotProfile,
    merged_analysis: dict,
) -> AssemblageDelta:
    """Calculate the delta between individual and merged development capacity."""

    # Lot area change (should be ~0, just confirming merge)
    individual_area = sum(l.lot_area or 0 for l in lots)
    merged_area = merged_lot.lot_area or 0
    lot_area_change = merged_area - individual_area

    # Lot type change
    individual_types = [l.lot_type for l in lots]
    lot_type_change = None
    if merged_lot.lot_type != individual_types[0] or len(set(individual_types)) > 1:
        type_desc = ", ".join(f"{l.bbl}: {l.lot_type}" for l in lots)
        lot_type_change = f"{type_desc} → {merged_lot.lot_type}"

    # Frontage change
    individual_frontage = sum(l.lot_frontage or 0 for l in lots)
    merged_frontage = merged_lot.lot_frontage or 0
    street_frontage_change = {
        "individual_total_ft": round(individual_frontage, 1),
        "merged_ft": round(merged_frontage, 1),
        "change_ft": round(merged_frontage - individual_frontage, 1),
    }

    # Footprint gain from side yard elimination
    footprint_gain = _calculate_footprint_gain(lots, merged_lot)

    # Per-scenario deltas
    scenario_deltas = _calculate_scenario_deltas(
        individual_analyses, merged_analysis, lots, merged_lot,
    )

    return AssemblageDelta(
        lot_area_change=round(lot_area_change, 0),
        lot_type_change=lot_type_change,
        street_frontage_change=street_frontage_change,
        footprint_gain_sf=round(footprint_gain, 0),
        scenario_deltas=scenario_deltas,
    )


def _calculate_footprint_gain(
    lots: list[LotProfile],
    merged_lot: LotProfile,
) -> float:
    """Calculate the footprint gain from eliminating side yards between lots.

    When lots are assembled, the side lot lines between them disappear,
    and any side yard requirements along those lines are eliminated.
    """
    # For individual lots: sum of buildable footprints
    # (width - 2*side_yard) * (depth - rear_yard)
    # For merged: full width * (depth - rear_yard)
    # The difference is the gain from eliminated side yards.

    # Simplified: assume all lots share the same depth and rear yard
    # Each interior lot loses side_yard on both sides.
    # When merged, only the two outer edges need side yards.

    # Count eliminated side yards
    n = len(lots)
    # Interior lots in a row: (n-1) shared boundaries, each saving 2 side yards
    # But shared boundaries only eliminate 2 side yards (one from each lot)
    # Total side yard eliminated = (n-1) * 2 * side_yard_width * depth

    # Use average depth
    avg_depth = sum(l.lot_depth or 100 for l in lots) / n if n > 0 else 100
    avg_rear = 30  # Standard rear yard

    # If lots don't require side yards, gain is 0
    # TODO: VERIFY — this assumes all lots in the assemblage had side yards
    # In practice, only R1-R3 and detached R4/R5 have side yards.
    # For attached R4/R5 and R6+, there are no side yards to eliminate.
    # The gain then comes from more efficient building envelope.
    side_yard = 5  # Typical R4/R5 side yard

    # This is a rough estimate — the actual gain depends on specific yards
    # of each lot's district
    effective_depth = avg_depth - avg_rear
    gain = (n - 1) * 2 * side_yard * effective_depth  # Both sides of each shared boundary

    # If lots are in R6+ (no side yards), the gain is primarily from
    # eliminating the gap between buildings and getting a more efficient plate
    return max(0, gain)


def _calculate_scenario_deltas(
    individual_analyses: list[dict],
    merged_analysis: dict,
    lots: list[LotProfile],
    merged_lot: LotProfile,
) -> list[ScenarioDelta]:
    """Calculate per-scenario deltas between individual and merged analyses."""

    # Sum up individual scenario metrics by scenario name
    individual_sums = {}
    for analysis in individual_analyses:
        for scenario in analysis.get("scenarios", []):
            name = scenario.name if hasattr(scenario, "name") else scenario.get("name", "")
            if name not in individual_sums:
                individual_sums[name] = {
                    "total_gross_sf": 0,
                    "zoning_floor_area": 0,
                    "max_height_ft": 0,
                    "total_units": 0,
                    "parking_required": 0,
                    "loss_factor_pct": 0,
                    "count": 0,
                }
            s = individual_sums[name]
            s["total_gross_sf"] += _get_attr(scenario, "total_gross_sf", 0)
            s["zoning_floor_area"] += _get_attr(scenario, "zoning_floor_area", 0) or 0
            s["max_height_ft"] = max(s["max_height_ft"], _get_attr(scenario, "max_height_ft", 0))
            s["total_units"] += _get_attr(scenario, "total_units", 0)
            parking = _get_attr(scenario, "parking", None)
            if parking:
                s["parking_required"] += (
                    parking.total_spaces_required
                    if hasattr(parking, "total_spaces_required")
                    else parking.get("total_spaces_required", 0)
                )
            lf = _get_attr(scenario, "loss_factor", None)
            if lf:
                pct = (lf.loss_factor_pct if hasattr(lf, "loss_factor_pct")
                       else lf.get("loss_factor_pct", 0))
                s["loss_factor_pct"] += pct
                s["count"] += 1

    # Average loss factor
    for name, s in individual_sums.items():
        if s["count"] > 0:
            s["loss_factor_pct"] /= s["count"]

    # Build deltas for each merged scenario
    deltas = []
    merged_lot_area = merged_lot.lot_area or 1

    for scenario in merged_analysis.get("scenarios", []):
        name = scenario.name if hasattr(scenario, "name") else scenario.get("name", "")
        merged_zfa = _get_attr(scenario, "zoning_floor_area", 0) or 0
        merged_gross = _get_attr(scenario, "total_gross_sf", 0)
        merged_height = _get_attr(scenario, "max_height_ft", 0)
        merged_units = _get_attr(scenario, "total_units", 0)
        merged_parking = 0
        parking = _get_attr(scenario, "parking", None)
        if parking:
            merged_parking = (
                parking.total_spaces_required
                if hasattr(parking, "total_spaces_required")
                else parking.get("total_spaces_required", 0)
            )
        merged_lf = 0
        lf = _get_attr(scenario, "loss_factor", None)
        if lf:
            merged_lf = (lf.loss_factor_pct if hasattr(lf, "loss_factor_pct")
                         else lf.get("loss_factor_pct", 0))

        merged_far = round(merged_zfa / merged_lot_area, 2) if merged_lot_area else 0

        # Find matching individual scenario
        ind = individual_sums.get(name, {})
        ind_zfa = ind.get("zoning_floor_area", 0)
        ind_gross = ind.get("total_gross_sf", 0)
        ind_height = ind.get("max_height_ft", 0)
        ind_units = ind.get("total_units", 0)
        ind_parking = ind.get("parking_required", 0)
        ind_lf = ind.get("loss_factor_pct", 0)
        individual_area = sum(l.lot_area or 0 for l in lots)
        ind_far = round(ind_zfa / individual_area, 2) if individual_area else 0

        notes = []
        additional_sf = merged_gross - ind_gross

        if additional_sf > 0:
            notes.append(
                f"Assemblage unlocks {additional_sf:,.0f} additional buildable SF."
            )
        if merged_height > ind_height:
            notes.append(
                f"Max height increases from {ind_height:.0f} ft to {merged_height:.0f} ft."
            )
        if merged_far > ind_far:
            notes.append(
                f"Effective FAR increases from {ind_far:.2f} to {merged_far:.2f}."
            )

        deltas.append(ScenarioDelta(
            scenario_name=name,
            far_delta=round(merged_far - ind_far, 2),
            zfa_delta=round(merged_zfa - ind_zfa, 0),
            height_delta=round(merged_height - ind_height, 0),
            unit_count_delta=merged_units - ind_units,
            parking_delta=merged_parking - ind_parking,
            loss_factor_delta=round(merged_lf - ind_lf, 1),
            additional_buildable_sf=round(additional_sf, 0),
            notes=notes,
        ))

    return deltas


def _get_attr(obj, attr: str, default=None):
    """Get attribute from object or dict."""
    if hasattr(obj, attr):
        return getattr(obj, attr)
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return default


# ──────────────────────────────────────────────────────────────────
# KEY UNLOCK IDENTIFICATION
# ──────────────────────────────────────────────────────────────────

def identify_key_unlocks(
    lots: list[LotProfile],
    merged_lot: LotProfile,
    delta: AssemblageDelta,
) -> list[str]:
    """Identify the key value drivers of the assemblage."""
    unlocks = []

    individual_types = set(l.lot_type for l in lots)

    # Through lot created
    if merged_lot.lot_type == "through" and "through" not in individual_types:
        unlocks.append(
            "Assemblage creates a through lot. Rear yard equivalent rules "
            "(ZR §23-532) apply instead of standard rear yard — may allow "
            "full lot coverage with rear yard equivalent distributed across "
            "upper floors."
        )

    # Corner lot created
    if merged_lot.lot_type == "corner" and "corner" not in individual_types:
        unlocks.append(
            "Assemblage creates a corner lot. Height and setback rules "
            "change per ZR §23-632/633. Corner lots may have higher lot "
            "coverage and different height/setback transitions."
        )

    # Lot width above thresholds
    merged_frontage = merged_lot.lot_frontage or 0
    individual_max_frontage = max((l.lot_frontage or 0) for l in lots)

    if merged_frontage >= 100 and individual_max_frontage < 100:
        unlocks.append(
            "Merged lot width exceeds 100 ft — tower-on-base rules may "
            "apply in R9/R10 districts."
        )

    if merged_frontage >= 45 and individual_max_frontage < 45:
        unlocks.append(
            "Merged lot width exceeds 45 ft — sliver law height restriction "
            "no longer applies (ZR §23-692). This eliminates the front wall "
            "height limit that caps buildings on narrow lots."
        )

    # Lot area thresholds
    merged_area = merged_lot.lot_area or 0
    individual_max_area = max((l.lot_area or 0) for l in lots)

    if merged_area >= 10000 and individual_max_area < 10000:
        unlocks.append(
            "Merged lot exceeds 10,000 SF — different lot coverage and "
            "open space rules may apply."
        )

    if merged_area >= 5000 and individual_max_area < 5000:
        unlocks.append(
            "Merged lot exceeds 5,000 SF — more efficient building "
            "footprint and lower loss factor achievable."
        )

    # Side yard elimination
    if delta.footprint_gain_sf > 0:
        unlocks.append(
            f"Elimination of side yards between lots increases buildable "
            f"footprint by approximately {delta.footprint_gain_sf:,.0f} SF "
            f"per floor."
        )

    # Split zone
    districts = set()
    for lot in lots:
        districts.update(lot.zoning_districts)
    if len(districts) > 1:
        unlocks.append(
            f"Individual lots are in different districts "
            f"({', '.join(sorted(districts))}). Assemblage may allow FAR "
            f"averaging across the site (ZR §77-02/03)."
        )

    # Maximum additional buildable SF across all scenarios
    if delta.scenario_deltas:
        max_delta = max(delta.scenario_deltas, key=lambda d: d.additional_buildable_sf)
        if max_delta.additional_buildable_sf > 0:
            unlocks.append(
                f"Best scenario ({max_delta.scenario_name}) unlocks "
                f"{max_delta.additional_buildable_sf:,.0f} additional buildable SF "
                f"and {max_delta.unit_count_delta} additional units."
            )

    return unlocks
