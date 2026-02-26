"""
Floor-by-floor massing builder for NYC zoning feasibility analysis.

Takes a DevelopmentScenario + lot geometry and generates a detailed
floor-by-floor massing model suitable for 3D rendering (Three.js)
and 2D section/plan views.

The builder:
  1. Starts with the lot polygon (GeoJSON or rectangular from PLUTO dimensions)
  2. Carves out required yards to get the buildable footprint
  3. Stacks floors with proper heights (ground 12-15 ft, typical 10 ft)
  4. Applies setbacks above base height for QH buildings
  5. Clips upper floors to sky exposure plane for HF buildings
  6. Handles tower-on-base massing (podium + tower)
  7. Adds bulkhead (stair/elevator overruns)
  8. Validates sanity checks (min floor plate, FAR cap, structural grid)
"""

from __future__ import annotations

import json
import math
from typing import Optional

from shapely.geometry import shape, Polygon, MultiPolygon, box, LineString
from shapely.ops import transform, unary_union
from shapely import affinity

from app.models.schemas import (
    ZoningEnvelope, MassingFloor, DevelopmentScenario, LotProfile,
)
from app.zoning_engine.height_setback import FLOOR_HEIGHTS, get_bulkhead_allowance
from app.zoning_engine.dormers import get_dormer_rules


# ──────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────

USE_COLORS = {
    "commercial":          "#4A90D9",
    "residential":         "#F5E6CC",
    "community_facility":  "#6BBF6B",
    "parking":             "#999999",
    "core":                "#555555",
    "mechanical":          "#777777",
    "cellar":              "#777777",
    "mixed":               "#D9A84A",
}

MIN_FLOOR_PLATE_SF = 400  # Below this, stop adding floors (roughly 20×20 studio)
STRUCTURAL_GRID_FT = 1.0   # Round dimensions to nearest foot


# ──────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────────────────────────

def build_massing_model(
    lot: LotProfile,
    scenario: DevelopmentScenario,
    envelope: ZoningEnvelope,
    district: str = "",
    lot_geojson: Optional[dict] = None,
) -> dict:
    """Build a detailed floor-by-floor massing model.

    Args:
        lot: LotProfile with dimensions and geometry
        scenario: DevelopmentScenario with floor list
        envelope: ZoningEnvelope with yards, heights, setbacks
        district: Zoning district code (for dormer rules)
        lot_geojson: GeoJSON polygon of the lot (optional — will use
                     rectangular approximation if not provided)

    Returns:
        Complete massing model dict for API/Three.js consumption.
    """
    lot_frontage = lot.lot_frontage or 50
    lot_depth = lot.lot_depth or 100
    lot_area = lot.lot_area or (lot_frontage * lot_depth)

    # Step 1: Get or create lot polygon in local feet coordinates
    lot_poly, origin = _get_lot_polygon(lot_geojson, lot_frontage, lot_depth)

    # Step 2: Identify street edges (front of lot)
    street_edges = _identify_street_edges(lot_poly, lot_frontage, lot_depth)

    # Step 3: Calculate buildable footprint (lot minus yards, then lot coverage cap)
    buildable = _calculate_buildable_footprint(
        lot_poly, envelope, lot_frontage, lot_depth, street_edges, lot_area,
    )

    if buildable.is_empty or not buildable.is_valid:
        return {"error": "Buildable footprint is empty after applying yards"}

    buildable_area = buildable.area

    # Step 4: Build floor-by-floor massing
    massing_floors = _build_floors(
        buildable=buildable,
        lot_poly=lot_poly,
        scenario=scenario,
        envelope=envelope,
        district=district,
        lot_frontage=lot_frontage,
        lot_depth=lot_depth,
        lot_area=lot_area,
        street_edges=street_edges,
    )

    # Step 5: Add bulkhead if applicable
    bulkhead = _add_bulkhead(
        massing_floors, scenario, envelope, district,
    )

    # Step 6: Compute the full zoning envelope wireframe
    zoning_envelope_geom = _compute_zoning_envelope(
        buildable, envelope, lot_poly, street_edges,
    )

    # Step 7: Sanity checks
    warnings = _run_sanity_checks(
        massing_floors, scenario, envelope, lot_area,
    )

    # Step 8: Build the 3D geometry (vertices + faces + colors)
    geometry_3d = _build_3d_geometry(massing_floors, bulkhead)

    # Assemble the response
    total_height = 0
    if massing_floors:
        last = massing_floors[-1]
        total_height = last["elevation_ft"] + last["height_ft"]
    if bulkhead:
        total_height = bulkhead["elevation_ft"] + bulkhead["height_ft"]

    return {
        "lot": {
            "polygon": _poly_to_coords(lot_poly),
            "area_sf": round(lot_area, 0),
            "frontage_ft": round(lot_frontage, 1),
            "depth_ft": round(lot_depth, 1),
            "street_edges": street_edges,
        },
        "buildable_footprint": {
            "polygon": _poly_to_coords(buildable),
            "area_sf": round(buildable_area, 0),
        },
        "scenarios": [
            {
                "name": scenario.name,
                "floors": massing_floors,
                "bulkhead": bulkhead,
                "zoning_envelope": zoning_envelope_geom,
                "summary": {
                    "total_zfa": scenario.zoning_floor_area or scenario.total_gross_sf,
                    "total_gross_sf": scenario.total_gross_sf,
                    "max_height": round(total_height, 1),
                    "floors": scenario.num_floors,
                    "units": scenario.total_units,
                    "loss_factor": (
                        scenario.loss_factor.loss_factor_pct
                        if scenario.loss_factor else 0
                    ),
                    "parking_spaces": (
                        scenario.parking.total_spaces_required
                        if scenario.parking else 0
                    ),
                    "far_used": scenario.far_used,
                },
            }
        ],
        "geometry_3d": geometry_3d,
        "origin": origin,
        "total_height_ft": round(total_height, 1),
        "warnings": warnings,
    }


# ──────────────────────────────────────────────────────────────────
# LOT POLYGON
# ──────────────────────────────────────────────────────────────────

def _get_lot_polygon(
    lot_geojson: Optional[dict],
    lot_frontage: float,
    lot_depth: float,
) -> tuple[Polygon, dict]:
    """Get or create the lot polygon in local feet coordinates.

    Returns (polygon_in_feet, origin_dict).
    """
    if lot_geojson:
        poly = shape(lot_geojson)
        if isinstance(poly, MultiPolygon):
            poly = max(poly.geoms, key=lambda p: p.area)

        centroid = poly.centroid
        local = _to_local_feet(poly, centroid.x, centroid.y)
        return local, {"lng": centroid.x, "lat": centroid.y}

    # No GeoJSON — create a rectangle oriented with frontage along the x-axis
    # Origin at bottom-left corner; front along y=0, rear at y=depth
    poly = box(0, 0, lot_frontage, lot_depth)
    return poly, {"lng": 0, "lat": 0}


def _to_local_feet(polygon: Polygon, origin_lng: float, origin_lat: float) -> Polygon:
    """Convert a lat/lng polygon to local coordinates in feet."""
    lat_rad = math.radians(origin_lat)
    lng_to_ft = math.cos(lat_rad) * 364567.2
    lat_to_ft = 364567.2

    def project(x, y, z=None):
        return ((x - origin_lng) * lng_to_ft, (y - origin_lat) * lat_to_ft)

    return transform(project, polygon)


# ──────────────────────────────────────────────────────────────────
# STREET EDGE IDENTIFICATION
# ──────────────────────────────────────────────────────────────────

def _identify_street_edges(
    lot_poly: Polygon, lot_frontage: float, lot_depth: float,
) -> list[dict]:
    """Identify which edges of the lot polygon face streets.

    For rectangular lots (generated from PLUTO dimensions), the front edge
    is the bottom (y=0) side. For real GeoJSON polygons, we use the
    longest edge as the front.
    """
    coords = list(lot_poly.exterior.coords)
    edges = []
    for i in range(len(coords) - 1):
        p1, p2 = coords[i], coords[i + 1]
        length = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
        edges.append({
            "edge": [[round(p1[0], 2), round(p1[1], 2)],
                     [round(p2[0], 2), round(p2[1], 2)]],
            "length": round(length, 1),
            "midpoint_y": (p1[1] + p2[1]) / 2,
        })

    if not edges:
        return []

    # For rectangular lots: front edge is the one closest to y=0
    min_y = min(e["midpoint_y"] for e in edges)
    street_edges = []
    for e in edges:
        is_front = abs(e["midpoint_y"] - min_y) < 1.0
        if is_front and abs(e["length"] - lot_frontage) < 5:
            street_edges.append({
                "edge": e["edge"],
                "street_name": "Street",
                "width": "narrow",
                "length": e["length"],
                "side": "front",
            })

    return street_edges


# ──────────────────────────────────────────────────────────────────
# BUILDABLE FOOTPRINT
# ──────────────────────────────────────────────────────────────────

def _calculate_buildable_footprint(
    lot_poly: Polygon,
    envelope: ZoningEnvelope,
    lot_frontage: float,
    lot_depth: float,
    street_edges: list[dict],
    lot_area: float = 0,
) -> Polygon:
    """Calculate the buildable footprint by subtracting required yards,
    then applying lot coverage maximum.

    Handles both axis-aligned and rotated rectangular lots by detecting
    rectangularity via minimum_rotated_rectangle, rotating to axis-align,
    applying yard/coverage calculations, and rotating back.

    Lot coverage max (ZR 23-15, 24-11) caps the building footprint as a
    percentage of the total lot area.  E.g. R6 interior = 65%.
    """
    poly_area = lot_poly.area
    actual_lot_area = lot_area if lot_area > 0 else poly_area

    # ── Rectangularity detection ────────────────────────────────────
    # Use minimum rotated rectangle to detect rotated-but-rectangular lots.
    min_rect = lot_poly.minimum_rotated_rectangle
    min_rect_area = min_rect.area
    is_rectangular = (
        min_rect_area > 0 and poly_area > 0
        and (poly_area / min_rect_area) > 0.85
    )

    if is_rectangular:
        return _buildable_for_rectangular_lot(
            lot_poly, min_rect, envelope,
            lot_frontage, lot_depth, actual_lot_area,
        )

    # ── Irregular lots: simplified buffering ────────────────────────
    avg_yard = (envelope.rear_yard + envelope.front_yard) / 2
    if envelope.side_yards_required:
        avg_yard = (avg_yard + envelope.side_yard_width) / 2
    inset = min(avg_yard / 2, 15)
    result = lot_poly.buffer(-inset)
    if result.is_empty or not result.is_valid:
        return lot_poly
    if isinstance(result, MultiPolygon):
        result = max(result.geoms, key=lambda p: p.area)

    # Apply lot coverage maximum
    if envelope.lot_coverage_max and actual_lot_area > 0:
        max_coverage_sf = actual_lot_area * (envelope.lot_coverage_max / 100)
        if result.area > max_coverage_sf:
            scale = math.sqrt(max_coverage_sf / result.area)
            centroid = result.centroid
            result = affinity.scale(result, xfact=scale, yfact=scale, origin=centroid)

    return result


def _buildable_for_rectangular_lot(
    lot_poly: Polygon,
    min_rect: Polygon,
    envelope,
    lot_frontage: float,
    lot_depth: float,
    lot_area: float,
) -> Polygon:
    """Compute buildable footprint for a rectangular lot that may be rotated.

    Strategy: determine the lot's rotation angle from its minimum rotated
    rectangle, rotate the polygon to axis-align it, apply yard setbacks
    and lot-coverage cap in axis-aligned space, then rotate back.
    """
    centroid = lot_poly.centroid

    # ── Determine rotation angle from the minimum rotated rectangle ──
    rect_coords = list(min_rect.exterior.coords)[:4]
    edges = []
    for i in range(4):
        p1, p2 = rect_coords[i], rect_coords[(i + 1) % 4]
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.sqrt(dx * dx + dy * dy)
        angle_deg = math.degrees(math.atan2(dy, dx))
        mid_y = (p1[1] + p2[1]) / 2
        edges.append({"length": length, "angle": angle_deg, "mid_y": mid_y})

    # Pair opposite edges: (0,2) and (1,3).
    # The pair whose average length is closer to lot_depth is the depth pair.
    avg_02 = (edges[0]["length"] + edges[2]["length"]) / 2
    avg_13 = (edges[1]["length"] + edges[3]["length"]) / 2

    if abs(avg_02 - lot_depth) <= abs(avg_13 - lot_depth):
        depth_angle = edges[0]["angle"]  # depth edge angle
    else:
        depth_angle = edges[1]["angle"]  # depth edge angle

    # ── Rotate polygon so that depth aligns with x-axis ──────────────
    aligned = affinity.rotate(lot_poly, -depth_angle, origin=centroid)
    ab = aligned.bounds
    aminx, aminy, amaxx, amaxy = ab
    aligned_width = amaxy - aminy   # frontage direction (y)
    aligned_depth = amaxx - aminx   # depth direction (x)

    # ── Determine which end of x is "front" (street) vs "rear" ───────
    # The front edge is the one closest to the street.
    # In local coords the street tends to be at the lower-y end of the
    # *original* polygon.  Transform the midpoint of the original polygon's
    # min-y edge into aligned space to find which x-end is "front".
    from shapely.geometry import Point as _Pt
    test_pt = _Pt(centroid.x, lot_poly.bounds[1])          # original min-y
    test_aligned = affinity.rotate(test_pt, -depth_angle, origin=centroid)
    front_at_aminx = (test_aligned.x - aminx) < (amaxx - test_aligned.x)

    # ── Apply yard setbacks ──────────────────────────────────────────
    side_yard = envelope.side_yard_width if envelope.side_yards_required else 0

    if front_at_aminx:
        bld_minx = aminx + envelope.front_yard
        bld_maxx = amaxx - envelope.rear_yard
    else:
        bld_minx = aminx + envelope.rear_yard
        bld_maxx = amaxx - envelope.front_yard

    bld_miny = aminy + side_yard
    bld_maxy = amaxy - side_yard

    if bld_minx >= bld_maxx or bld_miny >= bld_maxy:
        return Polygon()

    buildable = box(bld_minx, bld_miny, bld_maxx, bld_maxy)

    # ── Lot coverage cap — reduce from rear ──────────────────────────
    if envelope.lot_coverage_max and lot_area > 0:
        max_sf = lot_area * (envelope.lot_coverage_max / 100)
        if buildable.area > max_sf:
            width = bld_maxy - bld_miny
            if width > 0:
                max_depth = max_sf / width
                if front_at_aminx:
                    adj = min(bld_minx + max_depth, bld_maxx)
                    buildable = box(bld_minx, bld_miny, adj, bld_maxy)
                else:
                    adj = max(bld_maxx - max_depth, bld_minx)
                    buildable = box(adj, bld_miny, bld_maxx, bld_maxy)

    # ── Rotate back to original orientation ──────────────────────────
    return affinity.rotate(buildable, depth_angle, origin=centroid)


# ──────────────────────────────────────────────────────────────────
# FLOOR BUILDER
# ──────────────────────────────────────────────────────────────────

def _build_floors(
    buildable: Polygon,
    lot_poly: Polygon,
    scenario: DevelopmentScenario,
    envelope: ZoningEnvelope,
    district: str,
    lot_frontage: float,
    lot_depth: float,
    lot_area: float,
    street_edges: list[dict],
) -> list[dict]:
    """Build the floor-by-floor massing from the scenario's floor list."""

    floors = scenario.floors
    if not floors:
        return []

    # Dormer rules for this district
    dormer_rules = get_dormer_rules(district) if district else {"eligible": False}
    dormer_eligible = dormer_rules.get("eligible", False)
    dormer_width_pct = dormer_rules.get("max_width_pct", 0.60)

    base_height_max = envelope.base_height_max or 0
    sep = envelope.sky_exposure_plane

    massing_floors = []
    current_elevation = 0
    cumulative_zfa = 0
    max_zfa = scenario.zoning_floor_area or scenario.total_gross_sf

    for floor in floors:
        # Determine the floor plate polygon
        plate = _get_floor_plate(
            floor_num=floor.floor,
            elevation=current_elevation,
            buildable=buildable,
            envelope=envelope,
            base_height_max=base_height_max,
            dormer_eligible=dormer_eligible,
            dormer_width_pct=dormer_width_pct,
            sep=sep,
        )

        if plate.is_empty or not plate.is_valid:
            break

        # Check if this is a penthouse floor (gross_sf is much smaller than plate)
        # If the floor's gross_sf is ≤ 40% of the full plate, treat as penthouse
        # and reduce the footprint to match the specified area
        is_penthouse = (
            floor.gross_sf > 0
            and plate.area > 0
            and floor.gross_sf < plate.area * 0.40
        )
        if is_penthouse:
            # Create a centered reduced footprint for the penthouse
            scale = math.sqrt(floor.gross_sf / plate.area)
            centroid = plate.centroid
            plate = affinity.scale(plate, xfact=scale, yfact=scale, origin=centroid)

        plate_area = plate.area

        # Min floor plate check — stop if too small for efficient development
        # (skip check for first 2 floors — ground floor is always built)
        if floor.floor > 2 and plate_area < MIN_FLOOR_PLATE_SF:
            break

        # FAR check — don't exceed max ZFA
        remaining_zfa = max_zfa - cumulative_zfa
        actual_sf = min(floor.gross_sf, remaining_zfa) if remaining_zfa > 0 else floor.gross_sf

        # Compute setbacks relative to lot edges
        setbacks = _compute_setbacks(plate, lot_poly, buildable)

        massing_floors.append({
            "floor_num": floor.floor,
            "use": floor.use,
            "is_penthouse": is_penthouse,
            "elevation_ft": round(current_elevation, 1),
            "height_ft": round(floor.height_ft, 1),
            "footprint": _poly_to_coords(plate),
            "gross_area_sf": round(actual_sf, 0),
            "net_area_sf": round(floor.net_sf, 0),
            "plate_area_sf": round(plate_area, 0),
            "setback_from_street_ft": round(setbacks.get("front", 0), 1),
            "setback_from_rear_ft": round(setbacks.get("rear", 0), 1),
            "color": USE_COLORS.get(floor.use, "#CCCCCC"),
        })

        cumulative_zfa += actual_sf
        current_elevation += floor.height_ft

    return massing_floors


def _get_floor_plate(
    floor_num: int,
    elevation: float,
    buildable: Polygon,
    envelope: ZoningEnvelope,
    base_height_max: float,
    dormer_eligible: bool,
    dormer_width_pct: float,
    sep,
) -> Polygon:
    """Determine the floor plate polygon for a given floor.

    Applies:
      - QH setback above base height
      - Dormer adjustments
      - Sky exposure plane clipping
    """
    plate = buildable

    # Apply setback above base height (QH buildings)
    if (envelope.quality_housing and
            base_height_max > 0 and
            elevation >= base_height_max):
        setback = (envelope.setbacks.front_setback_above_base
                   if envelope.setbacks else 10)

        if dormer_eligible:
            # Dormer: partial setback — only non-dormer portion sets back
            reduced = setback * (1 - dormer_width_pct)
            plate = buildable.buffer(-reduced)
        else:
            plate = buildable.buffer(-setback)

        if plate.is_empty or not plate.is_valid:
            plate = buildable

        if isinstance(plate, MultiPolygon):
            plate = max(plate.geoms, key=lambda p: p.area)

    # Apply sky exposure plane clipping (HF buildings)
    if sep and elevation > sep.start_height:
        excess = elevation - sep.start_height
        inset = excess / sep.ratio
        plate = plate.buffer(-inset)
        if plate.is_empty or not plate.is_valid:
            return Polygon()
        if isinstance(plate, MultiPolygon):
            plate = max(plate.geoms, key=lambda p: p.area)

    return plate


def _compute_setbacks(
    plate: Polygon, lot_poly: Polygon, buildable: Polygon,
) -> dict:
    """Compute setbacks from street and rear lot lines."""
    lot_bounds = lot_poly.bounds  # minx, miny, maxx, maxy
    plate_bounds = plate.bounds

    return {
        "front": round(plate_bounds[1] - lot_bounds[1], 1),  # distance from front
        "rear": round(lot_bounds[3] - plate_bounds[3], 1),   # distance from rear
        "left": round(plate_bounds[0] - lot_bounds[0], 1),
        "right": round(lot_bounds[2] - plate_bounds[2], 1),
    }


# ──────────────────────────────────────────────────────────────────
# BULKHEAD
# ──────────────────────────────────────────────────────────────────

def _add_bulkhead(
    massing_floors: list[dict],
    scenario: DevelopmentScenario,
    envelope: ZoningEnvelope,
    district: str,
) -> Optional[dict]:
    """Add bulkhead (stair/elevator overruns) above the roof.

    Bulkheads are permitted obstructions per ZR 33-42.
    """
    if not massing_floors or scenario.num_floors < 3:
        return None

    # Only buildings with elevators/stairs get bulkheads
    core = scenario.core
    if not core or (core.stairs == 0 and core.elevators == 0):
        return None

    last_floor = massing_floors[-1]
    roof_elevation = last_floor["elevation_ft"] + last_floor["height_ft"]

    # Get lot area for bulkhead calculation — use scenario gross / num_floors as approx coverage
    approx_lot_area = last_floor.get("plate_area_sf", last_floor.get("gross_area_sf", 3000))
    bulkhead_allowance = get_bulkhead_allowance(approx_lot_area)
    raw_bh = bulkhead_allowance.get("max_height_above_roof", 12) if bulkhead_allowance else 12
    bulkhead_height = min(raw_bh, 12)  # Practical bulkhead = ~1 story, not legal max (25 ft)
    bulkhead_max_area = 20  # 20% of lot coverage per ZR 23-62

    # Bulkhead footprint: stair + elevator area
    stair_sf = core.stairs * core.stair_sf_per_floor
    elev_sf = core.elevators * core.elevator_sf_per_floor
    bulkhead_sf = stair_sf + elev_sf + 50  # +50 for mechanical

    # Cap at max % of top floor
    top_plate_area = last_floor.get("plate_area_sf", last_floor.get("gross_area_sf", 1000))
    max_sf = top_plate_area * (bulkhead_max_area / 100)
    bulkhead_sf = min(bulkhead_sf, max_sf)

    # Create a small rectangle for the bulkhead footprint
    # Centered on the top floor plate
    if last_floor.get("footprint"):
        top_plate = Polygon(last_floor["footprint"])
        centroid = top_plate.centroid
        # Square bulkhead roughly matching the needed area
        side = math.sqrt(bulkhead_sf)
        half = side / 2
        bh_poly = box(
            centroid.x - half, centroid.y - half,
            centroid.x + half, centroid.y + half,
        )
        # Intersect with top floor to keep it within bounds
        bh_poly = bh_poly.intersection(top_plate)
        if bh_poly.is_empty:
            bh_poly = box(
                centroid.x - half, centroid.y - half,
                centroid.x + half, centroid.y + half,
            )
        bh_coords = _poly_to_coords(bh_poly)
    else:
        bh_coords = []

    return {
        "footprint": bh_coords,
        "height_ft": bulkhead_height,
        "elevation_ft": round(roof_elevation, 1),
        "area_sf": round(bulkhead_sf, 0),
        "color": USE_COLORS["mechanical"],
    }


# ──────────────────────────────────────────────────────────────────
# ZONING ENVELOPE WIREFRAME
# ──────────────────────────────────────────────────────────────────

def _compute_zoning_envelope(
    buildable: Polygon,
    envelope: ZoningEnvelope,
    lot_poly: Polygon,
    street_edges: list[dict],
) -> dict:
    """Compute the zoning envelope geometry for overlay display.

    Returns wireframe edges + horizontal planes for:
      - Max height plane
      - Base height line
      - Sky exposure plane
      - Setback lines on ground
    """
    max_height = envelope.max_building_height or 200
    base_max = envelope.base_height_max or 0
    coords = list(buildable.exterior.coords[:-1])

    wireframe = []

    # Bottom edges
    for i in range(len(coords)):
        j = (i + 1) % len(coords)
        wireframe.append({
            "start": [round(coords[i][0], 2), round(coords[i][1], 2), 0],
            "end": [round(coords[j][0], 2), round(coords[j][1], 2), 0],
            "type": "ground",
        })

    # Vertical edges
    for x, y in coords:
        wireframe.append({
            "start": [round(x, 2), round(y, 2), 0],
            "end": [round(x, 2), round(y, 2), round(max_height, 1)],
            "type": "vertical",
        })

    # Max height plane edges
    for i in range(len(coords)):
        j = (i + 1) % len(coords)
        wireframe.append({
            "start": [round(coords[i][0], 2), round(coords[i][1], 2), round(max_height, 1)],
            "end": [round(coords[j][0], 2), round(coords[j][1], 2), round(max_height, 1)],
            "type": "max_height",
        })

    # Base height line (horizontal plane at base_max)
    if base_max > 0 and base_max < max_height:
        for i in range(len(coords)):
            j = (i + 1) % len(coords)
            wireframe.append({
                "start": [round(coords[i][0], 2), round(coords[i][1], 2), round(base_max, 1)],
                "end": [round(coords[j][0], 2), round(coords[j][1], 2), round(base_max, 1)],
                "type": "base_height",
            })

    # Sky exposure plane (angled surface)
    sep = envelope.sky_exposure_plane
    sky_exposure_plane = None
    if sep:
        sky_exposure_plane = {
            "start_height": sep.start_height,
            "ratio": sep.ratio,
            "direction": sep.direction,
        }

    return {
        "wireframe": wireframe,
        "max_height_ft": round(max_height, 1),
        "base_height_max_ft": round(base_max, 1) if base_max else None,
        "sky_exposure_plane": sky_exposure_plane,
        "setback_line": _poly_to_coords(buildable),
    }


# ──────────────────────────────────────────────────────────────────
# SANITY CHECKS
# ──────────────────────────────────────────────────────────────────

def _run_sanity_checks(
    massing_floors: list[dict],
    scenario: DevelopmentScenario,
    envelope: ZoningEnvelope,
    lot_area: float,
) -> list[str]:
    """Run sanity checks on the massing model."""
    warnings = []

    if not massing_floors:
        warnings.append("No floors could be built in the massing model.")
        return warnings

    # Check 1: Total ZFA vs max allowed
    total_built = sum(f["gross_area_sf"] for f in massing_floors)
    max_far = envelope.residential_far or 0
    max_zfa = max_far * lot_area
    if max_zfa > 0 and total_built > max_zfa * 1.05:
        warnings.append(
            f"Built area ({total_built:,.0f} SF) exceeds max ZFA "
            f"({max_zfa:,.0f} SF) by {total_built - max_zfa:,.0f} SF."
        )

    # Check 2: Height vs max height
    last = massing_floors[-1]
    built_height = last["elevation_ft"] + last["height_ft"]
    if envelope.max_building_height and built_height > envelope.max_building_height + 1:
        warnings.append(
            f"Building height ({built_height:.0f} ft) exceeds max allowed "
            f"({envelope.max_building_height:.0f} ft)."
        )

    # Check 3: Ground floor height
    ground = massing_floors[0]
    if ground["use"] == "commercial" and ground["height_ft"] < 14:
        warnings.append(
            f"Commercial ground floor height ({ground['height_ft']} ft) is below "
            f"typical minimum of 15 ft."
        )

    # Check 4: Minimum unit width sanity (if residential)
    for f in massing_floors:
        if f["use"] == "residential" and f.get("plate_area_sf", 0) > 0:
            # Assume roughly 2:1 aspect ratio for the plate
            plate_sf = f["plate_area_sf"]
            approx_width = math.sqrt(plate_sf / 2)
            if approx_width < 12:
                warnings.append(
                    f"Floor {f['floor_num']} plate is very narrow "
                    f"(~{approx_width:.0f} ft). Consider single-loaded corridor."
                )
                break  # Only warn once

    return warnings


# ──────────────────────────────────────────────────────────────────
# 3D GEOMETRY BUILDER
# ──────────────────────────────────────────────────────────────────

def _build_3d_geometry(
    massing_floors: list[dict],
    bulkhead: Optional[dict],
) -> dict:
    """Build Three.js-compatible geometry (vertices, faces, colors).

    Each floor is extruded from its footprint polygon. A small gap (0.3 ft)
    between floors provides visual separation.
    """
    vertices = []
    faces = []
    colors = []

    GAP = 0.3  # Visual gap between floors

    for floor in massing_floors:
        footprint = floor.get("footprint", [])
        if len(footprint) < 3:
            continue

        poly = Polygon(footprint)
        if poly.is_empty or not poly.is_valid:
            continue

        z_bottom = floor["elevation_ft"] + (GAP / 2 if floor["floor_num"] > 1 else 0)
        z_top = floor["elevation_ft"] + floor["height_ft"] - GAP / 2

        color = floor.get("color", "#CCCCCC")
        v_offset = len(vertices)
        floor_verts, floor_faces = _extrude_polygon(poly, z_bottom, z_top, v_offset)
        vertices.extend(floor_verts)
        faces.extend(floor_faces)
        colors.extend([color] * len(floor_faces))

    # Bulkhead geometry
    if bulkhead and bulkhead.get("footprint") and len(bulkhead["footprint"]) >= 3:
        bh_poly = Polygon(bulkhead["footprint"])
        if not bh_poly.is_empty and bh_poly.is_valid:
            z_bottom = bulkhead["elevation_ft"] + GAP
            z_top = bulkhead["elevation_ft"] + bulkhead["height_ft"]
            color = bulkhead.get("color", "#777777")
            v_offset = len(vertices)
            bh_verts, bh_faces = _extrude_polygon(bh_poly, z_bottom, z_top, v_offset)
            vertices.extend(bh_verts)
            faces.extend(bh_faces)
            colors.extend([color] * len(bh_faces))

    return {
        "vertices": vertices,
        "faces": faces,
        "colors": colors,
    }


def _extrude_polygon(
    polygon: Polygon, z_bottom: float, z_top: float, v_offset: int,
) -> tuple[list, list]:
    """Extrude a 2D polygon into a 3D solid between z_bottom and z_top."""
    coords = list(polygon.exterior.coords[:-1])
    n = len(coords)
    if n < 3:
        return [], []

    vertices = []
    faces = []

    # Bottom vertices
    for x, y in coords:
        vertices.append([round(x, 2), round(y, 2), round(z_bottom, 2)])
    # Top vertices
    for x, y in coords:
        vertices.append([round(x, 2), round(y, 2), round(z_top, 2)])

    # Side faces (quads split into triangles)
    for i in range(n):
        j = (i + 1) % n
        bl = v_offset + i
        br = v_offset + j
        tr = v_offset + n + j
        tl = v_offset + n + i
        faces.append([bl, br, tr])
        faces.append([bl, tr, tl])

    # Top face (fan triangulation)
    for i in range(1, n - 1):
        faces.append([v_offset + n, v_offset + n + i, v_offset + n + i + 1])

    # Bottom face
    for i in range(1, n - 1):
        faces.append([v_offset, v_offset + i + 1, v_offset + i])

    return vertices, faces


# ──────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────

def _poly_to_coords(polygon) -> list:
    """Convert a Shapely polygon to a list of [x, y] coordinate pairs."""
    if polygon.is_empty or not polygon.is_valid:
        return []
    try:
        coords = list(polygon.exterior.coords[:-1])
        return [[round(x, 2), round(y, 2)] for x, y in coords]
    except Exception:
        return []
