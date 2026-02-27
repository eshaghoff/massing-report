"""
Static map image fetcher for PDF report embedding.

Fetches satellite and street map images from ESRI (free, no auth) or
Google Maps Static API (if key configured).  Also provides Pillow-based
polygon overlay compositing and a ReportLab fallback drawing.

All functions return ``bytes | None`` — callers should handle the None
case by skipping the image or using the programmatic fallback.
"""

from __future__ import annotations

import logging
import math
from io import BytesIO
from typing import Optional

import httpx
from shapely.geometry import shape as shapely_shape, Polygon

from app.config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────
# BBOX HELPERS
# ──────────────────────────────────────────────────────────────────

FT_PER_LAT_DEG = 364567.2  # approximate feet per degree latitude at ~40.7°N


def compute_bbox_from_geometry(
    geometry: dict,
    padding_pct: float = 0.25,
) -> tuple[float, float, float, float]:
    """Compute a padded bounding box from a GeoJSON geometry.

    Returns (minx, miny, maxx, maxy) in WGS84 degrees.
    """
    poly = shapely_shape(geometry)
    minx, miny, maxx, maxy = poly.bounds
    dx = (maxx - minx) * padding_pct
    dy = (maxy - miny) * padding_pct
    # Ensure minimum extent (~200 ft) so very small lots are still visible
    min_extent_deg = 200 / FT_PER_LAT_DEG
    if dx < min_extent_deg:
        dx = min_extent_deg
    if dy < min_extent_deg:
        dy = min_extent_deg
    return (minx - dx, miny - dy, maxx + dx, maxy + dy)


def compute_bbox_from_latlng(
    lat: float,
    lng: float,
    radius_ft: float = 500,
) -> tuple[float, float, float, float]:
    """Compute a bounding box centred on a point with a given radius in feet."""
    lat_deg = radius_ft / FT_PER_LAT_DEG
    lng_deg = radius_ft / (math.cos(math.radians(lat)) * FT_PER_LAT_DEG)
    return (lng - lng_deg, lat - lat_deg, lng + lng_deg, lat + lat_deg)


# ──────────────────────────────────────────────────────────────────
# IMAGE FETCHING — ESRI
# ──────────────────────────────────────────────────────────────────

ESRI_SATELLITE_URL = (
    "https://server.arcgisonline.com/arcgis/rest/services/"
    "World_Imagery/MapServer/export"
)
ESRI_STREET_URL = (
    "https://server.arcgisonline.com/arcgis/rest/services/"
    "World_Street_Map/MapServer/export"
)
ESRI_LIGHT_GRAY_URL = (
    "https://server.arcgisonline.com/arcgis/rest/services/"
    "Canvas/World_Light_Gray_Base/MapServer/export"
)


async def _fetch_esri_image(
    base_url: str,
    bbox: tuple[float, float, float, float],
    width: int = 800,
    height: int = 600,
) -> bytes | None:
    """Fetch an image tile from an ESRI MapServer export endpoint."""
    params = {
        "bbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        "bboxSR": "4326",
        "imageSR": "4326",
        "size": f"{width},{height}",
        "format": "png32",
        "f": "image",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(base_url, params=params)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                return resp.content
            logger.warning("ESRI returned status %s for %s", resp.status_code, base_url)
            return None
    except Exception as exc:
        logger.warning("ESRI fetch failed (%s): %s", base_url, exc)
        return None


# ──────────────────────────────────────────────────────────────────
# IMAGE FETCHING — GOOGLE MAPS STATIC API
# ──────────────────────────────────────────────────────────────────

GOOGLE_STATIC_URL = "https://maps.googleapis.com/maps/api/staticmap"


def _encode_polygon_path(geometry: dict) -> str:
    """Encode a GeoJSON polygon as a Google Maps Static API path parameter.

    Format: ``fillcolor:0xRRGGBBAA|color:0xRRGGBBFF|weight:2|lat1,lng1|lat2,lng2|...``
    """
    coords = geometry.get("coordinates", [[]])[0]
    if not coords:
        return ""
    # Google expects lat,lng order (reversed from GeoJSON lng,lat)
    path_parts = [f"{c[1]},{c[0]}" for c in coords]
    return (
        "fillcolor:0x4A90D940|color:0x4A90D9FF|weight:3|"
        + "|".join(path_parts)
    )


async def _fetch_google_map(
    lat: float,
    lng: float,
    geometry: dict | None,
    maptype: str = "satellite",
    zoom: int = 17,
    width: int = 800,
    height: int = 600,
) -> bytes | None:
    """Fetch a map image from Google Maps Static API."""
    api_key = settings.google_maps_api_key
    if not api_key:
        return None

    params: dict = {
        "center": f"{lat},{lng}",
        "zoom": str(zoom),
        "size": f"{width}x{height}",
        "maptype": maptype,
        "key": api_key,
    }
    if geometry:
        path = _encode_polygon_path(geometry)
        if path:
            params["path"] = path

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(GOOGLE_STATIC_URL, params=params)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                return resp.content
            logger.warning("Google Maps returned status %s", resp.status_code)
            return None
    except Exception as exc:
        logger.warning("Google Maps fetch failed: %s", exc)
        return None


# ──────────────────────────────────────────────────────────────────
# POLYGON OVERLAY (Pillow)
# ──────────────────────────────────────────────────────────────────

def draw_lot_boundary_on_image(
    image_bytes: bytes,
    geometry: dict,
    bbox: tuple[float, float, float, float],
) -> bytes:
    """Overlay the lot polygon on a raster image using Pillow.

    Args:
        image_bytes: Raw PNG bytes of the base map image.
        geometry: GeoJSON polygon of the lot.
        bbox: (minx, miny, maxx, maxy) in WGS84 degrees matching the image extent.

    Returns:
        Modified PNG bytes with lot polygon overlaid.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        logger.warning("Pillow not installed — returning image without overlay")
        return image_bytes

    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    w, h = img.size
    minx, miny, maxx, maxy = bbox

    # Extract coordinate rings from GeoJSON (handles Polygon and MultiPolygon)
    geom_type = geometry.get("type", "")
    raw_coords = geometry.get("coordinates", [])
    rings: list[list] = []

    if geom_type == "Polygon":
        # coordinates = [ring, ...], first ring is exterior
        if raw_coords and raw_coords[0]:
            rings.append(raw_coords[0])
    elif geom_type == "MultiPolygon":
        # coordinates = [[ring, ...], [ring, ...], ...]
        for polygon_coords in raw_coords:
            if polygon_coords and polygon_coords[0]:
                rings.append(polygon_coords[0])
    else:
        # Unknown type — try to extract first ring heuristically
        if raw_coords:
            first = raw_coords[0]
            if first and isinstance(first[0], (list, tuple)):
                if isinstance(first[0][0], (int, float)):
                    # It's [[lng, lat], ...] — a ring
                    rings.append(first)
                elif isinstance(first[0][0], (list, tuple)):
                    # It's [[[lng, lat], ...]] — polygon inside multipolygon
                    if first[0]:
                        rings.append(first[0])

    if not rings:
        return image_bytes

    # Map GeoJSON coords (lng, lat) to pixel coords
    def to_px(lng: float, lat: float) -> tuple[float, float]:
        px = (lng - minx) / (maxx - minx) * w
        py = (maxy - lat) / (maxy - miny) * h  # Y is inverted
        return (px, py)

    # Draw semi-transparent fill + solid outline for each ring
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for ring in rings:
        pixel_coords = [to_px(float(c[0]), float(c[1])) for c in ring]
        if len(pixel_coords) < 3:
            continue
        # Fill: light blue, 25% opacity
        draw.polygon(pixel_coords, fill=(74, 144, 217, 64))
        # Outline: solid blue, 3px
        draw.polygon(pixel_coords, outline=(74, 144, 217, 255))
        for i in range(len(pixel_coords)):
            p1 = pixel_coords[i]
            p2 = pixel_coords[(i + 1) % len(pixel_coords)]
            draw.line([p1, p2], fill=(74, 144, 217, 255), width=3)

    composited = Image.alpha_composite(img, overlay)
    buf = BytesIO()
    composited.save(buf, format="PNG")
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────
# REPORTLAB FALLBACK DRAWING
# ──────────────────────────────────────────────────────────────────

def draw_lot_diagram_reportlab(
    geometry: dict | None,
    lot_area: float | None = None,
    lot_frontage: float | None = None,
    lot_depth: float | None = None,
    rear_yard: float = 30,
    front_yard: float = 0,
    side_yards: bool = False,
    side_yard_width: float = 0,
    width: float = 468,  # 6.5 inches in points
    height: float = 300,
) -> "Drawing":
    """Create a ReportLab Drawing of the lot boundary with yard setbacks.

    This is the fallback when satellite/street images are unavailable.
    """
    from reportlab.graphics.shapes import Drawing, Polygon as RLPolygon, Rect, String, Line
    from reportlab.lib import colors

    BLUE = colors.HexColor('#4A90D9')
    LIGHT_BLUE = colors.HexColor('#4A90D960')
    GREY = colors.HexColor('#666666')
    LIGHT_GREY = colors.HexColor('#e0e0e0')
    GREEN = colors.HexColor('#6BBF6B40')
    RED_LIGHT = colors.HexColor('#FF666630')

    d = Drawing(width, height)
    margin = 40

    # Background
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor('#f8f9fa'), strokeColor=None))

    draw_w = width - 2 * margin
    draw_h = height - 2 * margin

    if geometry and geometry.get("coordinates"):
        # Use actual GeoJSON polygon
        coords = geometry["coordinates"][0]
        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        gminx, gmaxx = min(lngs), max(lngs)
        gminy, gmaxy = min(lats), max(lats)
        gw = gmaxx - gminx or 0.0001
        gh = gmaxy - gminy or 0.0001

        # Map to drawing coords
        def to_draw(lng, lat):
            x = margin + (lng - gminx) / gw * draw_w
            y = margin + (lat - gminy) / gh * draw_h
            return (x, y)

        points = []
        for c in coords:
            px, py = to_draw(c[0], c[1])
            points.extend([px, py])

        # Lot fill
        d.add(RLPolygon(points, fillColor=LIGHT_BLUE, strokeColor=BLUE, strokeWidth=2))

    elif lot_frontage and lot_depth:
        # Fallback: draw a rectangle from frontage × depth
        ft_w = lot_frontage
        ft_h = lot_depth
        scale = min(draw_w / ft_w, draw_h / ft_h)

        rect_w = ft_w * scale
        rect_h = ft_h * scale
        rx = margin + (draw_w - rect_w) / 2
        ry = margin + (draw_h - rect_h) / 2

        # Lot boundary
        d.add(Rect(rx, ry, rect_w, rect_h, fillColor=LIGHT_BLUE, strokeColor=BLUE, strokeWidth=2))

        # Rear yard
        if rear_yard > 0:
            ry_h = rear_yard * scale
            d.add(Rect(rx, ry + rect_h - ry_h, rect_w, ry_h,
                        fillColor=RED_LIGHT, strokeColor=colors.HexColor('#FF6666'), strokeWidth=0.5))
            d.add(String(rx + rect_w / 2, ry + rect_h - ry_h / 2 - 4,
                         f"Rear Yard ({rear_yard:.0f}')", fontSize=7,
                         fillColor=GREY, textAnchor='middle'))

        # Front yard
        if front_yard > 0:
            fy_h = front_yard * scale
            d.add(Rect(rx, ry, rect_w, fy_h,
                        fillColor=RED_LIGHT, strokeColor=colors.HexColor('#FF6666'), strokeWidth=0.5))
            d.add(String(rx + rect_w / 2, ry + fy_h / 2 - 4,
                         f"Front Yard ({front_yard:.0f}')", fontSize=7,
                         fillColor=GREY, textAnchor='middle'))

        # Side yards
        if side_yards and side_yard_width > 0:
            sy_w = side_yard_width * scale
            # Left
            d.add(Rect(rx, ry, sy_w, rect_h,
                        fillColor=RED_LIGHT, strokeColor=colors.HexColor('#FF6666'), strokeWidth=0.5))
            # Right
            d.add(Rect(rx + rect_w - sy_w, ry, sy_w, rect_h,
                        fillColor=RED_LIGHT, strokeColor=colors.HexColor('#FF6666'), strokeWidth=0.5))

        # Dimension labels
        d.add(String(rx + rect_w / 2, ry - 12,
                     f"Frontage: {ft_w:.0f}'", fontSize=8,
                     fillColor=GREY, textAnchor='middle'))
        d.add(String(rx - 12, ry + rect_h / 2,
                     f"{ft_h:.0f}'", fontSize=8,
                     fillColor=GREY, textAnchor='middle'))

        # Street label
        d.add(String(rx + rect_w / 2, ry - 24,
                     "▼ STREET ▼", fontSize=9,
                     fillColor=colors.HexColor('#333333'), textAnchor='middle'))

    else:
        # No geometry data at all
        d.add(String(width / 2, height / 2,
                     "Lot geometry not available",
                     fontSize=12, fillColor=GREY, textAnchor='middle'))

    # Area label (top-right)
    if lot_area:
        d.add(String(width - margin, height - 15,
                     f"Lot Area: {lot_area:,.0f} SF", fontSize=8,
                     fillColor=GREY, textAnchor='end'))

    return d


# ──────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────

async def fetch_satellite_image(
    lat: float,
    lng: float,
    geometry: dict | None = None,
    zoom: int = 17,
    width: int = 800,
    height: int = 600,
) -> bytes | None:
    """Fetch a satellite/aerial image with lot boundary overlaid.

    Tries: ESRI World Imagery → Google Maps Static API → None.
    If ESRI is used (no native polygon support), the polygon is composited
    via Pillow.
    """
    bbox = (
        compute_bbox_from_geometry(geometry)
        if geometry
        else compute_bbox_from_latlng(lat, lng)
    )

    # Try ESRI first (free, no auth)
    img = await _fetch_esri_image(ESRI_SATELLITE_URL, bbox, width, height)
    if img and geometry:
        # Overlay polygon via Pillow
        try:
            img = draw_lot_boundary_on_image(img, geometry, bbox)
        except Exception as e:
            logger.warning("Polygon overlay failed: %s — returning image without overlay", e)
    if img:
        return img

    # Try Google Maps (if key set — has native polygon overlay)
    img = await _fetch_google_map(lat, lng, geometry, maptype="satellite", zoom=zoom, width=width, height=height)
    if img:
        return img

    return None


async def fetch_street_map_image(
    lat: float,
    lng: float,
    geometry: dict | None = None,
    zoom: int = 16,
    width: int = 800,
    height: int = 600,
) -> bytes | None:
    """Fetch a street/context map image with lot boundary overlaid.

    Tries: ESRI World Street Map → Google Maps Static API → None.
    """
    bbox = (
        compute_bbox_from_geometry(geometry)
        if geometry
        else compute_bbox_from_latlng(lat, lng)
    )

    # Try ESRI first
    img = await _fetch_esri_image(ESRI_STREET_URL, bbox, width, height)
    if img and geometry:
        try:
            img = draw_lot_boundary_on_image(img, geometry, bbox)
        except Exception as e:
            logger.warning("Polygon overlay failed on street map: %s", e)
    if img:
        return img

    # Try Google Maps
    img = await _fetch_google_map(lat, lng, geometry, maptype="roadmap", zoom=zoom, width=width, height=height)
    if img:
        return img

    return None


# ──────────────────────────────────────────────────────────────────
# ZONING MAP
# ──────────────────────────────────────────────────────────────────

NYC_ZONING_FEATURE_URL = (
    "https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/"
    "nyzd/FeatureServer/0/query"
)

# Color coding for zoning district types
ZONING_DISTRICT_COLORS = {
    "R": (255, 235, 130, 130),   # Residential: warm yellow
    "C": (240, 140, 140, 130),   # Commercial: red
    "M": (190, 160, 230, 130),   # Manufacturing: purple
    "P": (140, 210, 140, 130),   # Park: green
    "BPC": (255, 200, 150, 130), # Battery Park City: orange
}


async def fetch_zoning_map_image(
    lat: float,
    lng: float,
    geometry: dict | None = None,
    width: int = 800,
    height: int = 600,
) -> bytes | None:
    """Fetch a zoning district map with the subject property marked.

    Visual improvements:
    - Light gray canvas base map (less visual clutter)
    - Opaque district fills (alpha=130) so zones are clearly visible
    - Thick district boundary lines (2px dark gray)
    - White background boxes behind district labels for legibility
    - Larger label font (14pt)
    - Subject property with white halo (7px white behind 4px blue)
    - Colour legend in bottom-right corner

    Returns PNG bytes or None if all sources fail.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("Pillow not installed — cannot create zoning map")
        return None

    # Use wider bbox for neighborhood context
    bbox = (
        compute_bbox_from_geometry(geometry, padding_pct=0.8)
        if geometry
        else compute_bbox_from_latlng(lat, lng, radius_ft=1000)
    )
    minx, miny, maxx, maxy = bbox

    # Step 1: Fetch LIGHT GRAY base map (much cleaner than street map)
    base_img = await _fetch_esri_image(ESRI_LIGHT_GRAY_URL, bbox, width, height)
    if not base_img:
        # Fallback to street map
        base_img = await _fetch_esri_image(ESRI_STREET_URL, bbox, width, height)
    if not base_img:
        base_img = await _fetch_esri_image(ESRI_SATELLITE_URL, bbox, width, height)
    if not base_img:
        return None

    img = Image.open(BytesIO(base_img)).convert("RGBA")
    w, h = img.size

    def geo_to_px(gx: float, gy: float) -> tuple[float, float]:
        """Convert WGS84 coords to pixel coords."""
        px = (gx - minx) / (maxx - minx) * w
        py = (maxy - gy) / (maxy - miny) * h
        return (px, py)

    # Load font
    try:
        label_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except Exception:
        try:
            label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except Exception:
            label_font = ImageFont.load_default()

    try:
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
    except Exception:
        small_font = ImageFont.load_default()

    # Step 2: Query zoning districts within bbox
    districts_geojson = await _fetch_zoning_districts(bbox)

    # Step 3: Overlay zoning districts with improved visuals
    legend_entries = {}  # zone_prefix -> color for legend

    if districts_geojson:
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        for feature in districts_geojson.get("features", []):
            props = feature.get("properties", {})
            zone_code = props.get("ZONEDIST", "")
            geom = feature.get("geometry", {})
            geom_type = geom.get("type", "")

            # Determine color by district prefix
            color = (200, 200, 200, 100)  # Default gray
            zone_prefix = ""
            for prefix, c in ZONING_DISTRICT_COLORS.items():
                if zone_code.upper().startswith(prefix):
                    color = c
                    zone_prefix = prefix
                    break

            # Track for legend
            if zone_prefix and zone_prefix not in legend_entries:
                legend_entries[zone_prefix] = color

            # Extract coordinate rings
            rings = []
            if geom_type == "Polygon":
                coords = geom.get("coordinates", [])
                if coords and coords[0]:
                    rings.append(coords[0])
            elif geom_type == "MultiPolygon":
                for poly in geom.get("coordinates", []):
                    if poly and poly[0]:
                        rings.append(poly[0])

            # Draw each ring
            for ring in rings:
                pixel_pts = [geo_to_px(float(c[0]), float(c[1])) for c in ring]
                if len(pixel_pts) >= 3:
                    # Opaque fill
                    draw.polygon(pixel_pts, fill=tuple(color))
                    # Thick dark gray border (2px)
                    border_color = (100, 100, 100, 200)
                    for k in range(len(pixel_pts)):
                        p1 = pixel_pts[k]
                        p2 = pixel_pts[(k + 1) % len(pixel_pts)]
                        draw.line([p1, p2], fill=border_color, width=2)

                    # Label district code at centroid with white background
                    if pixel_pts and zone_code:
                        cx = sum(p[0] for p in pixel_pts) / len(pixel_pts)
                        cy = sum(p[1] for p in pixel_pts) / len(pixel_pts)
                        # Only label if centroid is within image bounds
                        if 30 < cx < w - 30 and 30 < cy < h - 30:
                            try:
                                # Measure text size
                                text_bbox = draw.textbbox((0, 0), zone_code, font=label_font)
                                tw = text_bbox[2] - text_bbox[0]
                                th = text_bbox[3] - text_bbox[1]
                                # White background box with padding
                                pad = 3
                                draw.rectangle(
                                    [cx - tw/2 - pad, cy - th/2 - pad,
                                     cx + tw/2 + pad, cy + th/2 + pad],
                                    fill=(255, 255, 255, 210),
                                )
                                draw.text(
                                    (cx, cy), zone_code,
                                    fill=(60, 60, 60, 240),
                                    anchor="mm",
                                    font=label_font,
                                )
                            except Exception:
                                try:
                                    draw.text(
                                        (cx - 15, cy - 7), zone_code,
                                        fill=(60, 60, 60, 240),
                                        font=label_font,
                                    )
                                except Exception:
                                    pass

        img = Image.alpha_composite(img, overlay)

    # Step 4: Mark subject property with white halo
    if geometry:
        overlay2 = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw2 = ImageDraw.Draw(overlay2)

        geom_type = geometry.get("type", "")
        raw_coords = geometry.get("coordinates", [])
        rings = []
        if geom_type == "Polygon":
            if raw_coords and raw_coords[0]:
                rings.append(raw_coords[0])
        elif geom_type == "MultiPolygon":
            for poly in raw_coords:
                if poly and poly[0]:
                    rings.append(poly[0])

        for ring in rings:
            pixel_pts = [geo_to_px(float(c[0]), float(c[1])) for c in ring]
            if len(pixel_pts) >= 3:
                # Blue fill
                draw2.polygon(pixel_pts, fill=(74, 144, 217, 140))
                # White halo (7px) behind blue outline (4px)
                for k in range(len(pixel_pts)):
                    p1 = pixel_pts[k]
                    p2 = pixel_pts[(k + 1) % len(pixel_pts)]
                    draw2.line([p1, p2], fill=(255, 255, 255, 220), width=7)
                for k in range(len(pixel_pts)):
                    p1 = pixel_pts[k]
                    p2 = pixel_pts[(k + 1) % len(pixel_pts)]
                    draw2.line([p1, p2], fill=(74, 144, 217, 255), width=4)

        # Red pin at centroid
        pin_x, pin_y = geo_to_px(lng, lat) if lat and lng else (w / 2, h / 2)
        r = 7
        draw2.ellipse([pin_x - r, pin_y - r, pin_x + r, pin_y + r],
                      fill=(220, 50, 50, 255), outline=(255, 255, 255, 255), width=2)

        img = Image.alpha_composite(img, overlay2)

    # Step 5: Draw legend in bottom-right corner
    if legend_entries:
        legend_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        legend_draw = ImageDraw.Draw(legend_overlay)

        legend_labels = {
            "R": "Residential",
            "C": "Commercial",
            "M": "Manufacturing",
            "P": "Park",
            "BPC": "Battery Park City",
        }

        items = [(prefix, legend_labels.get(prefix, prefix), color)
                 for prefix, color in legend_entries.items()]

        # Legend dimensions
        item_h = 18
        legend_h = len(items) * item_h + 28  # header + items + padding
        legend_w = 140
        lx = w - legend_w - 15
        ly = h - legend_h - 15

        # Background
        legend_draw.rectangle([lx, ly, lx + legend_w, ly + legend_h],
                              fill=(255, 255, 255, 220), outline=(180, 180, 180, 200))

        # Title
        try:
            legend_draw.text((lx + 8, ly + 4), "Zoning Districts",
                             fill=(60, 60, 60, 255), font=small_font)
        except Exception:
            pass

        # Items
        for i, (prefix, label_text, color) in enumerate(items):
            y_pos = ly + 22 + i * item_h
            # Color swatch
            swatch_color = (color[0], color[1], color[2], 200)
            legend_draw.rectangle([lx + 8, y_pos, lx + 22, y_pos + 12],
                                  fill=swatch_color, outline=(100, 100, 100, 180))
            # Label
            try:
                legend_draw.text((lx + 28, y_pos - 1), label_text,
                                 fill=(60, 60, 60, 255), font=small_font)
            except Exception:
                pass

        img = Image.alpha_composite(img, legend_overlay)

    # Convert to RGB for PNG export
    final = img.convert("RGB")
    buf = BytesIO()
    final.save(buf, format="PNG")
    return buf.getvalue()


async def fetch_context_map_image(
    lat: float,
    lng: float,
    geometry: dict | None = None,
    width: int = 800,
    height: int = 500,
) -> bytes | None:
    """Fetch a zoomed-out context map showing roughly half of NYC.

    Uses a wide bounding box (~3 miles / ~15,000 ft radius) so the
    viewer can see the property's neighborhood context within the borough.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        logger.warning("Pillow not installed — cannot create context map")
        return None

    # ~15,000 ft radius ≈ roughly half-borough scale
    bbox = compute_bbox_from_latlng(lat, lng, radius_ft=15000)
    minx, miny, maxx, maxy = bbox

    # Fetch base street map at this zoom
    base_img = await _fetch_esri_image(ESRI_STREET_URL, bbox, width, height)
    if not base_img:
        return None

    img = Image.open(BytesIO(base_img)).convert("RGBA")
    w, h = img.size

    def geo_to_px(gx: float, gy: float) -> tuple[float, float]:
        px = (gx - minx) / (maxx - minx) * w
        py = (maxy - gy) / (maxy - miny) * h
        return (px, py)

    # Draw a bold marker at the property location
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    pin_x, pin_y = geo_to_px(lng, lat)

    # Outer ring (red)
    r_outer = 12
    draw.ellipse(
        [pin_x - r_outer, pin_y - r_outer, pin_x + r_outer, pin_y + r_outer],
        fill=(220, 50, 50, 200), outline=(255, 255, 255, 255), width=3,
    )
    # Inner dot (white)
    r_inner = 4
    draw.ellipse(
        [pin_x - r_inner, pin_y - r_inner, pin_x + r_inner, pin_y + r_inner],
        fill=(255, 255, 255, 255),
    )

    # Label
    try:
        draw.text(
            (pin_x + 16, pin_y - 8), "Subject Property",
            fill=(220, 50, 50, 255),
        )
    except Exception:
        pass

    img = Image.alpha_composite(img, overlay)
    final = img.convert("RGB")
    buf = BytesIO()
    final.save(buf, format="PNG")
    return buf.getvalue()


async def fetch_city_overview_map(
    lat: float,
    lng: float,
    width: int = 800,
    height: int = 500,
) -> bytes | None:
    """Fetch a full NYC overview map showing all 5 boroughs with a property marker.

    Uses a fixed bounding box covering the entire NYC metro area so the viewer
    can see exactly where in the city the property is located.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("Pillow not installed — cannot create city overview map")
        return None

    # Fixed bbox covering all 5 boroughs of NYC
    bbox = (-74.30, 40.48, -73.68, 40.93)
    minx, miny, maxx, maxy = bbox

    # Fetch base street map at city scale
    base_img = await _fetch_esri_image(ESRI_STREET_URL, bbox, width, height)
    if not base_img:
        return None

    img = Image.open(BytesIO(base_img)).convert("RGBA")
    w, h = img.size

    def geo_to_px(gx: float, gy: float) -> tuple[float, float]:
        px = (gx - minx) / (maxx - minx) * w
        py = (maxy - gy) / (maxy - miny) * h
        return (px, py)

    # Draw a bold marker at the property location
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    pin_x, pin_y = geo_to_px(lng, lat)

    # Outer glow ring
    r_glow = 18
    draw.ellipse(
        [pin_x - r_glow, pin_y - r_glow, pin_x + r_glow, pin_y + r_glow],
        fill=(220, 50, 50, 80),
    )

    # Main red circle
    r_outer = 12
    draw.ellipse(
        [pin_x - r_outer, pin_y - r_outer, pin_x + r_outer, pin_y + r_outer],
        fill=(220, 50, 50, 220), outline=(255, 255, 255, 255), width=3,
    )

    # Inner white dot
    r_inner = 4
    draw.ellipse(
        [pin_x - r_inner, pin_y - r_inner, pin_x + r_inner, pin_y + r_inner],
        fill=(255, 255, 255, 255),
    )

    # Label with background
    label = "Subject Property"
    try:
        # Draw label background
        label_x = pin_x + 18
        label_y = pin_y - 10
        draw.rectangle(
            [label_x - 2, label_y - 2, label_x + 110, label_y + 14],
            fill=(255, 255, 255, 200),
        )
        draw.text(
            (label_x, label_y), label,
            fill=(220, 50, 50, 255),
        )
    except Exception:
        pass

    img = Image.alpha_composite(img, overlay)
    final = img.convert("RGB")
    buf = BytesIO()
    final.save(buf, format="PNG")
    return buf.getvalue()




# ──────────────────────────────────────────────────────────────────
# BBOX SQUARE HELPER
# ──────────────────────────────────────────────────────────────────

def _make_bbox_square(bbox: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """Take any bbox and return a square bbox centered on the same point.

    The square side length equals the larger of width/height.
    """
    minx, miny, maxx, maxy = bbox
    cx = (minx + maxx) / 2
    cy = (miny + maxy) / 2
    dx = (maxx - minx) / 2
    dy = (maxy - miny) / 2
    half = max(dx, dy)
    return (cx - half, cy - half, cx + half, cy + half)


# ──────────────────────────────────────────────────────────────────
# NEIGHBOURHOOD MAP
# ──────────────────────────────────────────────────────────────────

async def fetch_neighborhood_map_image(
    lat: float,
    lng: float,
    geometry: dict | None = None,
    width: int = 800,
    height: int = 600,
) -> bytes | None:
    """Fetch a neighborhood-level map (~0.75 mile radius) with subject property marker.

    Uses ESRI Street Map at ~4000ft radius for neighborhood context — wider than
    the close-up street map but tighter than the city overview.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("Pillow not installed — cannot create neighborhood map")
        return None

    # ~4000ft radius ~ 0.75 mile — good neighborhood context
    bbox = compute_bbox_from_latlng(lat, lng, radius_ft=4000)
    minx, miny, maxx, maxy = bbox

    # Fetch base street map at neighborhood scale
    base_img = await _fetch_esri_image(ESRI_STREET_URL, bbox, width, height)
    if not base_img:
        return None

    img = Image.open(BytesIO(base_img)).convert("RGBA")
    w, h = img.size

    def geo_to_px(gx: float, gy: float) -> tuple[float, float]:
        px = (gx - minx) / (maxx - minx) * w
        py = (maxy - gy) / (maxy - miny) * h
        return (px, py)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    pin_x, pin_y = geo_to_px(lng, lat)

    # Outer glow ring
    r_glow = 16
    draw.ellipse(
        [pin_x - r_glow, pin_y - r_glow, pin_x + r_glow, pin_y + r_glow],
        fill=(220, 50, 50, 80),
    )
    # Main red circle
    r_outer = 10
    draw.ellipse(
        [pin_x - r_outer, pin_y - r_outer, pin_x + r_outer, pin_y + r_outer],
        fill=(220, 50, 50, 220), outline=(255, 255, 255, 255), width=3,
    )
    # Inner white dot
    r_inner = 3
    draw.ellipse(
        [pin_x - r_inner, pin_y - r_inner, pin_x + r_inner, pin_y + r_inner],
        fill=(255, 255, 255, 255),
    )

    # Label with background
    label = "Subject Property"
    try:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except Exception:
            font = ImageFont.load_default()
        label_x = pin_x + 16
        label_y = pin_y - 8
        draw.rectangle(
            [label_x - 3, label_y - 2, label_x + 120, label_y + 15],
            fill=(255, 255, 255, 210),
        )
        draw.text((label_x, label_y), label, fill=(220, 50, 50, 255), font=font)
    except Exception:
        pass

    img = Image.alpha_composite(img, overlay)
    final = img.convert("RGB")
    buf = BytesIO()
    final.save(buf, format="PNG")
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────
# STREET VIEW (GOOGLE)
# ──────────────────────────────────────────────────────────────────

GOOGLE_STREETVIEW_URL = "https://maps.googleapis.com/maps/api/streetview"

async def fetch_street_view_image(
    lat: float,
    lng: float,
    width: int = 640,
    height: int = 480,
) -> bytes | None:
    """Fetch a street-level image from Google Street View Static API.

    Uses the Google Maps API key to request a street view image at the
    given coordinates.  Returns image bytes or None if no coverage / no
    key / error.
    """
    api_key = settings.google_maps_api_key
    if not api_key:
        logger.info("No Google Maps API key configured \u2014 skipping street view")
        return None

    params = {
        "size": f"{width}x{height}",
        "location": f"{lat},{lng}",
        "fov": "90",
        "heading": "0",
        "pitch": "10",
        "key": api_key,
        "source": "outdoor",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # First check metadata to see if coverage exists
            meta_params = {**params}
            meta_params.pop("size", None)
            meta_resp = await client.get(
                f"{GOOGLE_STREETVIEW_URL}/metadata", params=meta_params
            )
            if meta_resp.status_code == 200:
                meta = meta_resp.json()
                if meta.get("status") != "OK":
                    logger.info(
                        "No Google Street View coverage near %.6f, %.6f (status=%s)",
                        lat, lng, meta.get("status"),
                    )
                    return None

            # Fetch the actual image
            img_resp = await client.get(GOOGLE_STREETVIEW_URL, params=params)
            if img_resp.status_code == 200 and img_resp.headers.get(
                "content-type", ""
            ).startswith("image"):
                return img_resp.content
            logger.warning(
                "Google Street View fetch returned status %s", img_resp.status_code
            )
            return None

    except Exception as exc:
        logger.warning("Google Street View fetch failed: %s", exc)
        return None

async def _fetch_zoning_districts(
    bbox: tuple[float, float, float, float],
) -> dict | None:
    """Query NYC zoning district polygons from ArcGIS FeatureServer."""
    minx, miny, maxx, maxy = bbox
    geometry_json = f"{minx},{miny},{maxx},{maxy}"
    params = {
        "where": "1=1",
        "geometry": geometry_json,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "outFields": "ZONEDIST",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(NYC_ZONING_FEATURE_URL, params=params)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("Zoning districts query returned status %s", resp.status_code)
            return None
    except Exception as e:
        logger.warning("Zoning districts fetch failed: %s", e)
        return None
