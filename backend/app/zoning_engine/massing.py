"""
3D massing envelope computation.

Takes lot polygon (GeoJSON) + zoning parameters and generates 3D geometry
(vertices + faces) suitable for Three.js rendering.
"""

from __future__ import annotations

import json
import math
from typing import Optional

from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import transform
from shapely import affinity

from app.models.schemas import ZoningEnvelope, MassingFloor
from app.zoning_engine.height_setback import FLOOR_HEIGHTS
from app.zoning_engine.dormers import get_dormer_rules


def compute_massing_geometry(
    lot_geojson: dict,
    envelope: ZoningEnvelope,
    floors: list[MassingFloor],
    lot_frontage_bearing: float = 0,
    district: str = "",
) -> dict:
    """Compute 3D massing geometry for a development scenario.

    Args:
        lot_geojson: GeoJSON Polygon of the lot boundary
        envelope: Calculated zoning envelope
        floors: List of floors from the scenario
        lot_frontage_bearing: Bearing angle of the lot frontage (degrees from N)

    Returns dict with:
        vertices: list of [x, y, z] in local coordinates (feet)
        faces: list of [i, j, k] vertex indices
        floor_plates: list of floor plate polygons at each level
        colors: list of hex color per face (by use type)
        envelope_vertices: full zoning envelope wireframe
    """
    if not lot_geojson or not floors:
        return {}

    # Parse the lot polygon
    lot_poly = shape(lot_geojson)
    if isinstance(lot_poly, MultiPolygon):
        lot_poly = max(lot_poly.geoms, key=lambda p: p.area)

    # Convert from lat/lng to approximate local feet coordinates
    # Use centroid as origin
    centroid = lot_poly.centroid
    local_poly = _to_local_feet(lot_poly, centroid.x, centroid.y)

    # Build the buildable polygon (lot minus yards)
    buildable = _apply_yards(local_poly, envelope)

    # Build 3D geometry floor by floor
    vertices = []
    faces = []
    colors = []
    floor_plates = []
    current_height = 0

    use_colors = {
        "residential": "#4A90D9",
        "commercial": "#D94A4A",
        "community_facility": "#4AD97A",
        "parking": "#888888",
        "mixed": "#D9A84A",
    }

    # Check dormer eligibility for this district
    dormer_rules = get_dormer_rules(district) if district else {"eligible": False}
    dormer_eligible = dormer_rules.get("eligible", False)
    dormer_width_pct = dormer_rules.get("max_width_pct", 0.60)

    for floor in floors:
        # Determine floor plate polygon
        if floor.floor == 1:
            plate = buildable
        else:
            # Apply setback above base height if needed
            if (envelope.quality_housing and
                    envelope.base_height_max and
                    current_height >= envelope.base_height_max):
                setback = envelope.setbacks.front_setback_above_base if envelope.setbacks else 10

                if dormer_eligible:
                    # Dormer: only (1 - dormer_width_pct) of the frontage sets back.
                    # Use a reduced buffer to approximate the partial setback.
                    # The dormer portion rises straight up; the rest sets back.
                    reduced_setback = setback * (1 - dormer_width_pct)
                    plate = buildable.buffer(-reduced_setback)
                else:
                    plate = buildable.buffer(-setback)

                if plate.is_empty:
                    plate = buildable
            else:
                plate = buildable

        # Apply sky exposure plane clipping if applicable
        if (envelope.sky_exposure_plane and
                current_height > envelope.sky_exposure_plane.start_height):
            excess = current_height - envelope.sky_exposure_plane.start_height
            inset = excess / envelope.sky_exposure_plane.ratio
            plate = plate.buffer(-inset)
            if plate.is_empty:
                break

        if plate.is_empty or not plate.is_valid:
            break

        # Add vertices and faces for this floor
        color = use_colors.get(floor.use, "#CCCCCC")
        v_offset = len(vertices)
        floor_verts, floor_faces = _extrude_polygon(
            plate, current_height, current_height + floor.height_ft, v_offset,
        )
        vertices.extend(floor_verts)
        faces.extend(floor_faces)
        colors.extend([color] * len(floor_faces))

        # Store floor plate as GeoJSON for front-end hover display
        floor_plates.append({
            "floor": floor.floor,
            "use": floor.use,
            "height": current_height,
            "polygon": json.loads(
                json.dumps(plate.__geo_interface__)
            ),
        })

        current_height += floor.height_ft

    # Full zoning envelope wireframe
    envelope_verts = _compute_envelope_wireframe(
        buildable, envelope, current_height,
    )

    return {
        "vertices": vertices,
        "faces": faces,
        "colors": colors,
        "floor_plates": floor_plates,
        "envelope_wireframe": envelope_verts,
        "origin": {"lng": centroid.x, "lat": centroid.y},
        "total_height_ft": current_height,
    }


def _to_local_feet(polygon: Polygon, origin_lng: float, origin_lat: float) -> Polygon:
    """Convert a lat/lng polygon to local coordinates in feet.
    Uses simple equirectangular projection centered on the origin.
    """
    lat_rad = math.radians(origin_lat)
    # Degrees to feet conversion at this latitude
    lng_to_ft = math.cos(lat_rad) * 364567.2  # ~111,320 m/deg * 3.28084 ft/m
    lat_to_ft = 364567.2  # ~111,320 m/deg * 3.28084 ft/m

    def project(x, y, z=None):
        return ((x - origin_lng) * lng_to_ft, (y - origin_lat) * lat_to_ft)

    return transform(project, polygon)


def _apply_yards(polygon: Polygon, envelope: ZoningEnvelope) -> Polygon:
    """Shrink polygon by required yards.

    This is simplified — ideally we'd identify front/rear/side edges
    and apply different setbacks to each. For now, we use a buffer
    approximation based on rear yard (largest) offset from the back edge.
    """
    # Simple approach: inset the polygon by the rear yard from the longest edge
    # and front yard from the shortest edge
    # For a more accurate approach, we'd need to know which edge is the front
    if envelope.rear_yard > 0:
        # Approximate by insetting the polygon
        inset = min(envelope.rear_yard / 2, 15)  # Conservative inset
        result = polygon.buffer(-inset)
        if result.is_empty or not result.is_valid:
            return polygon
        return result
    return polygon


def _extrude_polygon(
    polygon: Polygon, z_bottom: float, z_top: float, v_offset: int,
) -> tuple[list, list]:
    """Extrude a 2D polygon into a 3D solid between z_bottom and z_top.

    Returns (vertices, faces) where vertices are [x, y, z] and
    faces are [i, j, k] triangles.
    """
    coords = list(polygon.exterior.coords[:-1])  # Remove closing point
    n = len(coords)
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
        # Bottom-left, bottom-right, top-right, top-left
        bl = v_offset + i
        br = v_offset + j
        tr = v_offset + n + j
        tl = v_offset + n + i
        faces.append([bl, br, tr])
        faces.append([bl, tr, tl])

    # Top face (fan triangulation from first vertex)
    for i in range(1, n - 1):
        faces.append([v_offset + n, v_offset + n + i, v_offset + n + i + 1])

    # Bottom face
    for i in range(1, n - 1):
        faces.append([v_offset, v_offset + i + 1, v_offset + i])

    return vertices, faces


def _compute_envelope_wireframe(
    buildable: Polygon, envelope: ZoningEnvelope, building_height: float,
) -> list:
    """Compute the full zoning envelope wireframe for reference display."""
    max_height = envelope.max_building_height or building_height * 1.2
    coords = list(buildable.exterior.coords[:-1])

    wireframe = []
    # Bottom edges
    for i in range(len(coords)):
        j = (i + 1) % len(coords)
        wireframe.append({
            "start": [coords[i][0], coords[i][1], 0],
            "end": [coords[j][0], coords[j][1], 0],
        })
    # Vertical edges
    for x, y in coords:
        wireframe.append({
            "start": [x, y, 0],
            "end": [x, y, max_height],
        })
    # Top edges
    for i in range(len(coords)):
        j = (i + 1) % len(coords)
        wireframe.append({
            "start": [coords[i][0], coords[i][1], max_height],
            "end": [coords[j][0], coords[j][1], max_height],
        })

    return wireframe
