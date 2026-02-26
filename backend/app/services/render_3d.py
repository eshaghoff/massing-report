"""
Static 3D massing renderer for PDF report embedding.

Uses matplotlib's mpl_toolkits.mplot3d to generate perspective and plan-view
images of building massing models.  Each floor is rendered as an extruded
polygon, colored by use type, with dimension annotations and a legend.

All inputs come from ``build_massing_model()`` in ``massing_builder.py``.
"""

from __future__ import annotations

import io
import logging
import math
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server-side rendering

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────
# USE-TYPE COLORS (match massing_builder.py palette)
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

USE_LABELS = {
    "commercial":          "Commercial",
    "residential":         "Residential",
    "community_facility":  "Community Facility",
    "parking":             "Parking",
    "mechanical":          "Mechanical",
    "mixed":               "Mixed Use",
}

# Face shading multipliers for 3D effect
SHADE_TOP = 1.0
SHADE_FRONT = 0.82
SHADE_RIGHT = 0.65


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert '#RRGGBB' to (r, g, b) in 0-1 range."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _shade(rgb: tuple, factor: float) -> tuple[float, float, float, float]:
    """Darken/lighten an RGB tuple and return RGBA."""
    return (
        max(0, min(1, rgb[0] * factor)),
        max(0, min(1, rgb[1] * factor)),
        max(0, min(1, rgb[2] * factor)),
        1.0,
    )


# ──────────────────────────────────────────────────────────────────
# FLOOR EXTRUSION HELPERS
# ──────────────────────────────────────────────────────────────────

def _extrude_floor_faces(
    footprint: list[list[float]],
    z_bottom: float,
    z_top: float,
    color_hex: str,
) -> list[tuple[list, tuple]]:
    """Create 3D polygon faces for one extruded floor.

    Returns list of (vertices_3d, rgba_color) tuples for Poly3DCollection.
    Each face is a list of [x, y, z] vertices.
    """
    if len(footprint) < 3:
        return []

    rgb = _hex_to_rgb(color_hex)
    faces = []

    # Top face
    top_verts = [[p[0], p[1], z_top] for p in footprint]
    faces.append((top_verts, _shade(rgb, SHADE_TOP)))

    # Bottom face (only visible from below — skip for performance)
    # bottom_verts = [[p[0], p[1], z_bottom] for p in footprint]
    # faces.append((bottom_verts, _shade(rgb, SHADE_TOP)))

    # Side faces
    n = len(footprint)
    for i in range(n):
        j = (i + 1) % n
        x0, y0 = footprint[i]
        x1, y1 = footprint[j]

        # Determine shading based on face normal direction
        dx = x1 - x0
        dy = y1 - y0
        # Outward normal (perpendicular to edge, pointing outward)
        nx, ny = -dy, dx
        # Shade based on normal direction relative to isometric "light"
        # Light comes from upper-right in standard view
        dot = nx * 0.7 + ny * (-0.3)
        if dot > 0:
            shade_factor = SHADE_FRONT
        else:
            shade_factor = SHADE_RIGHT

        quad = [
            [x0, y0, z_bottom],
            [x1, y1, z_bottom],
            [x1, y1, z_top],
            [x0, y0, z_top],
        ]
        faces.append((quad, _shade(rgb, shade_factor)))

    return faces


# ──────────────────────────────────────────────────────────────────
# PERSPECTIVE (3D) VIEW
# ──────────────────────────────────────────────────────────────────

def render_perspective_view(
    massing_model: dict,
    scenario_name: str = "",
    width: int = 800,
    height: int = 550,
    dpi: int = 150,
    elevation: float = 25,
    azimuth: float = -50,
) -> bytes:
    """Render an isometric-style 3D perspective view of the massing model.

    Args:
        massing_model: Output from ``build_massing_model()``.
        scenario_name: Title text for the image.
        width/height: Image dimensions in pixels.
        dpi: Render resolution.
        elevation/azimuth: Camera angles for the 3D view.

    Returns:
        PNG image bytes.
    """
    scenarios = massing_model.get("scenarios", [])
    if not scenarios:
        return b""
    scenario = scenarios[0]
    floors = scenario.get("floors", [])
    if not floors:
        return b""

    lot_poly = massing_model.get("lot", {}).get("polygon", [])
    buildable_poly = massing_model.get("buildable_footprint", {}).get("polygon", [])
    bulkhead = scenario.get("bulkhead")
    total_height = massing_model.get("total_height_ft", 0)

    # ── Figure setup ──
    fig_w = width / dpi
    fig_h = height / dpi
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi, facecolor="white")

    # Main 3D axes (leave room for legend on right)
    ax = fig.add_axes([0.02, 0.02, 0.78, 0.90], projection="3d")
    ax.set_facecolor("white")
    ax.view_init(elev=elevation, azim=azimuth)

    # ── Collect all coordinates for auto-scaling ──
    all_x, all_y, all_z = [], [], [0]
    for f in floors:
        fp = f.get("footprint", [])
        for pt in fp:
            all_x.append(pt[0])
            all_y.append(pt[1])
        all_z.append(f.get("elevation_ft", 0) + f.get("height_ft", 0))
    for pt in lot_poly:
        all_x.append(pt[0])
        all_y.append(pt[1])

    if not all_x:
        plt.close(fig)
        return b""

    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    z_max = max(all_z) if all_z else 50

    # Add padding
    x_pad = max((x_max - x_min) * 0.15, 5)
    y_pad = max((y_max - y_min) * 0.15, 5)
    z_pad = z_max * 0.1

    ax.set_xlim(x_min - x_pad, x_max + x_pad)
    ax.set_ylim(y_min - y_pad, y_max + y_pad)
    ax.set_zlim(0, z_max + z_pad)

    # ── Draw ground plane (lot boundary) ──
    if lot_poly and len(lot_poly) >= 3:
        lot_face = [[p[0], p[1], 0] for p in lot_poly]
        ground = Poly3DCollection(
            [lot_face],
            alpha=0.15,
            facecolors=[(0.85, 0.85, 0.85, 0.3)],
            edgecolors=[(0.5, 0.5, 0.5, 0.8)],
            linewidths=1.0,
        )
        ax.add_collection3d(ground)

    # ── Draw buildable footprint ──
    if buildable_poly and len(buildable_poly) >= 3:
        build_face = [[p[0], p[1], 0] for p in buildable_poly]
        buildable_col = Poly3DCollection(
            [build_face],
            alpha=0.2,
            facecolors=[(0.29, 0.56, 0.85, 0.2)],
            edgecolors=[(0.29, 0.56, 0.85, 0.5)],
            linewidths=0.8,
            linestyles="dashed",
        )
        ax.add_collection3d(buildable_col)

    # ── Draw floors (bottom to top) ──
    used_colors = {}
    for floor in sorted(floors, key=lambda f: f.get("elevation_ft", 0)):
        fp = floor.get("footprint", [])
        if len(fp) < 3:
            continue
        z_bot = floor.get("elevation_ft", 0)
        z_top = z_bot + floor.get("height_ft", 10)
        use = floor.get("use", "residential")
        color = floor.get("color", USE_COLORS.get(use, "#CCCCCC"))

        faces = _extrude_floor_faces(fp, z_bot, z_top, color)
        for verts, rgba in faces:
            poly = Poly3DCollection(
                [verts],
                alpha=0.92,
                facecolors=[rgba],
                edgecolors=[(0.25, 0.25, 0.25, 0.6)],
                linewidths=0.5,
            )
            ax.add_collection3d(poly)

        # Track used colors for legend
        label = USE_LABELS.get(use, use.replace("_", " ").title())
        if label not in used_colors:
            used_colors[label] = color

    # ── Draw floor separation lines (horizontal outlines at each floor boundary) ──
    for floor in sorted(floors, key=lambda f: f.get("elevation_ft", 0)):
        fp = floor.get("footprint", [])
        if len(fp) < 3:
            continue
        z_bot = floor.get("elevation_ft", 0)
        z_top = z_bot + floor.get("height_ft", 10)
        # Draw bottom edge of floor (horizontal line around footprint)
        for z_line in [z_bot, z_top]:
            line_verts = [[p[0], p[1], z_line] for p in fp] + [[fp[0][0], fp[0][1], z_line]]
            xs = [v[0] for v in line_verts]
            ys = [v[1] for v in line_verts]
            zs = [v[2] for v in line_verts]
            ax.plot(xs, ys, zs, color="#333333", linewidth=0.6, alpha=0.7)

    # ── Draw bulkhead ──
    if bulkhead and bulkhead.get("footprint"):
        bh_fp = bulkhead["footprint"]
        bh_z_bot = bulkhead.get("elevation_ft", z_max)
        bh_z_top = bh_z_bot + bulkhead.get("height_ft", 15)
        bh_color = bulkhead.get("color", "#777777")
        faces = _extrude_floor_faces(bh_fp, bh_z_bot, bh_z_top, bh_color)
        for verts, rgba in faces:
            poly = Poly3DCollection(
                [verts],
                alpha=0.85,
                facecolors=[rgba],
                edgecolors=[(0.3, 0.3, 0.3, 0.6)],
                linewidths=0.5,
            )
            ax.add_collection3d(poly)
        used_colors["Bulkhead"] = bh_color

    # ── Floor labels with area on side ──
    for floor in floors:
        fp = floor.get("footprint", [])
        if not fp:
            continue
        floor_num = floor.get("floor_num", floor.get("floor", 0))
        floor_area = floor.get("gross_area_sf", floor.get("plate_area_sf", 0))
        z_mid = floor.get("elevation_ft", 0) + floor.get("height_ft", 10) / 2
        # Place label near the right-front edge of the building
        fp_arr = np.array(fp)
        scores = fp_arr[:, 0] - fp_arr[:, 1]
        best_idx = np.argmax(scores)
        lx, ly = fp_arr[best_idx]
        # Show floor number + area
        area_str = f"F{floor_num} ({floor_area:,.0f} SF)" if floor_area else f"F{floor_num}"
        ax.text(
            lx + 2, ly - 2, z_mid,
            area_str,
            fontsize=4.5, color="#333333", fontweight="bold",
            ha="left", va="center",
            zdir="x",
        )

    # ── Dimension annotations ──
    if total_height > 0 and floors:
        fp_arr = np.array(floors[0].get("footprint", [[0, 0]]))
        rx = fp_arr[:, 0].max() + 8
        ry = fp_arr[:, 1].mean()

        # Total height dimension line (right side)
        ax.plot([rx, rx], [ry, ry], [0, total_height],
                color="#D94A4A", linewidth=1.5, linestyle="-")
        for z in [0, total_height]:
            ax.plot([rx - 1, rx + 1], [ry, ry], [z, z],
                    color="#D94A4A", linewidth=1.0)
        ax.text(rx + 3, ry, total_height / 2,
                f"{total_height:.0f} ft",
                fontsize=6, color="#D94A4A", fontweight="bold",
                ha="left", va="center")

        # Per-floor height tick marks (left side of dimension line)
        rx2 = rx - 4
        for floor in sorted(floors, key=lambda f: f.get("elevation_ft", 0)):
            z_bot = floor.get("elevation_ft", 0)
            z_top = z_bot + floor.get("height_ft", 10)
            ht = floor.get("height_ft", 10)
            z_mid = (z_bot + z_top) / 2
            # Small tick at floor boundary
            ax.plot([rx2, rx2 + 2], [ry, ry], [z_bot, z_bot],
                    color="#888888", linewidth=0.5)
            # Floor height label
            ax.text(rx2 - 1, ry, z_mid,
                    f"{ht:.0f}'",
                    fontsize=4, color="#888888",
                    ha="right", va="center")
        # Top tick
        ax.plot([rx2, rx2 + 2], [ry, ry], [total_height, total_height],
                color="#888888", linewidth=0.5)

        # Width dimension on ground (front edge of building)
        fp0 = floors[0].get("footprint", [])
        if len(fp0) >= 2:
            fp0_arr = np.array(fp0)
            # Find front edge (min y)
            y_front = fp0_arr[:, 1].min()
            x_left = fp0_arr[:, 0].min()
            x_right = fp0_arr[:, 0].max()
            width_ft = x_right - x_left
            z_dim = -3
            ax.plot([x_left, x_right], [y_front - 2, y_front - 2], [z_dim, z_dim],
                    color="#2C5F8A", linewidth=1.0)
            ax.text((x_left + x_right) / 2, y_front - 4, z_dim,
                    f"{width_ft:.0f}'",
                    fontsize=5, color="#2C5F8A", fontweight="bold",
                    ha="center", va="top")

            # Depth dimension on ground (side edge)
            y_rear = fp0_arr[:, 1].max()
            depth_ft = y_rear - y_front
            ax.plot([x_left - 2, x_left - 2], [y_front, y_rear], [z_dim, z_dim],
                    color="#2C5F8A", linewidth=1.0)
            ax.text(x_left - 4, (y_front + y_rear) / 2, z_dim,
                    f"{depth_ft:.0f}'",
                    fontsize=5, color="#2C5F8A", fontweight="bold",
                    ha="right", va="center")

    # ── Clean up axes ──
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_zlabel("")
    ax.tick_params(labelsize=5, colors="#999999")

    # Make axes less prominent — remove grid
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor("white")
    ax.yaxis.pane.set_edgecolor("white")
    ax.zaxis.pane.set_edgecolor("white")
    ax.grid(False)  # Remove background grid per user request

    # ── Title ──
    title = scenario_name or "Building Massing"
    ax.set_title(title, fontsize=10, fontweight="bold", color="#1a1a2e", pad=5)

    # ── Legend (right side of figure) ──
    legend_patches = []
    for label, color_hex in used_colors.items():
        rgb = _hex_to_rgb(color_hex)
        legend_patches.append(mpatches.Patch(color=rgb, label=label))

    if legend_patches:
        legend_ax = fig.add_axes([0.80, 0.30, 0.18, 0.40])
        legend_ax.axis("off")
        legend_ax.set_title("Uses", fontsize=8, fontweight="bold", loc="left",
                           color="#1a1a2e")
        for i, patch in enumerate(legend_patches):
            y = 0.9 - i * 0.15
            legend_ax.add_patch(
                plt.Rectangle((0.05, y - 0.04), 0.15, 0.08,
                              facecolor=patch.get_facecolor(),
                              edgecolor="#666666", linewidth=0.5,
                              transform=legend_ax.transAxes, clip_on=False)
            )
            legend_ax.text(0.25, y, patch.get_label(),
                          fontsize=7, va="center",
                          transform=legend_ax.transAxes, color="#333333")

    # ── Summary stats below legend ──
    summary = scenario.get("summary", {})
    if summary:
        stats_ax = fig.add_axes([0.80, 0.05, 0.18, 0.22])
        stats_ax.axis("off")
        stats_lines = []
        if summary.get("total_gross_sf"):
            stats_lines.append(f"Gross SF: {summary['total_gross_sf']:,.0f}")
        if summary.get("floors"):
            stats_lines.append(f"Floors: {summary['floors']}")
        if summary.get("max_height"):
            stats_lines.append(f"Height: {summary['max_height']:.0f} ft")
        if summary.get("units"):
            stats_lines.append(f"Units: {summary['units']}")
        if summary.get("far_used"):
            stats_lines.append(f"FAR: {summary['far_used']:.2f}")

        for i, line in enumerate(stats_lines):
            stats_ax.text(0.05, 0.9 - i * 0.18, line,
                         fontsize=7, va="top",
                         transform=stats_ax.transAxes, color="#333333")

    # ── Render to PNG bytes ──
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────
# PLAN (TOP-DOWN) VIEW
# ──────────────────────────────────────────────────────────────────

def _annotate_edge_length(
    ax, p1: list[float], p2: list[float],
    offset: float = 2.0,
    fontsize: float = 6,
    color: str = "#444444",
) -> None:
    """Annotate the length of a polygon edge at its midpoint.

    Places the label slightly outward from the polygon edge.
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1.0:
        return  # skip tiny edges

    mx = (p1[0] + p2[0]) / 2
    my = (p1[1] + p2[1]) / 2

    # Outward normal (perpendicular)
    if length > 0:
        nx = -dy / length
        ny = dx / length
    else:
        nx, ny = 0, 0

    # Offset label outward
    lx = mx + nx * offset
    ly = my + ny * offset

    # Rotation angle for text to follow edge direction
    angle = math.degrees(math.atan2(dy, dx))
    # Keep text readable (flip if upside-down)
    if angle > 90:
        angle -= 180
    elif angle < -90:
        angle += 180

    ax.text(
        lx, ly, f"{length:.0f}'",
        fontsize=fontsize, color=color, fontweight="bold",
        ha="center", va="center",
        rotation=angle,
        rotation_mode="anchor",
        bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                  edgecolor="none", alpha=0.8),
    )


def render_plan_view(
    massing_model: dict,
    scenario_name: str = "",
    width: int = 600,
    height: int = 600,
    dpi: int = 150,
) -> bytes:
    """Render a top-down plan view showing floor plate outlines.

    Shows nested floor plates at each level, lot boundary, and yard lines.

    Args:
        massing_model: Output from ``build_massing_model()``.
        scenario_name: Title text.
        width/height: Image dimensions in pixels.
        dpi: Render resolution.

    Returns:
        PNG image bytes.
    """
    scenarios = massing_model.get("scenarios", [])
    if not scenarios:
        return b""
    scenario = scenarios[0]
    floors = scenario.get("floors", [])
    if not floors:
        return b""

    lot_poly = massing_model.get("lot", {}).get("polygon", [])
    buildable_poly = massing_model.get("buildable_footprint", {}).get("polygon", [])

    fig_w = width / dpi
    fig_h = height / dpi
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi, facecolor="white")
    ax.set_facecolor("white")
    ax.set_aspect("equal")

    # ── Draw lot boundary ──
    if lot_poly and len(lot_poly) >= 3:
        lot_arr = np.array(lot_poly + [lot_poly[0]])  # close polygon
        ax.plot(lot_arr[:, 0], lot_arr[:, 1],
                color="#666666", linewidth=1.5, linestyle="--",
                label="Lot Boundary")
        ax.fill(lot_arr[:, 0], lot_arr[:, 1],
                alpha=0.05, color="#999999")
        # Annotate lot edge lengths
        for k in range(len(lot_poly)):
            k2 = (k + 1) % len(lot_poly)
            _annotate_edge_length(ax, lot_poly[k], lot_poly[k2],
                                  offset=3.5, fontsize=6, color="#555555")

    # ── Draw buildable footprint ──
    if buildable_poly and len(buildable_poly) >= 3:
        bp_arr = np.array(buildable_poly + [buildable_poly[0]])
        ax.plot(bp_arr[:, 0], bp_arr[:, 1],
                color="#4A90D9", linewidth=2.0, linestyle="-",
                label="Buildable Footprint")
        ax.fill(bp_arr[:, 0], bp_arr[:, 1],
                alpha=0.20, color="#4A90D9")
        # Annotate buildable footprint edge lengths
        for k in range(len(buildable_poly)):
            k2 = (k + 1) % len(buildable_poly)
            _annotate_edge_length(ax, buildable_poly[k], buildable_poly[k2],
                                  offset=2.0, fontsize=5.5, color="#2C5F8A")

        # ── Yard dimension arrows (between lot boundary and buildable footprint) ──
        if lot_poly and len(lot_poly) >= 3:
            lot_arr_np = np.array(lot_poly)
            bp_arr_np = np.array(buildable_poly)
            lot_minx, lot_miny = lot_arr_np.min(axis=0)
            lot_maxx, lot_maxy = lot_arr_np.max(axis=0)
            bp_minx, bp_miny = bp_arr_np.min(axis=0)
            bp_maxx, bp_maxy = bp_arr_np.max(axis=0)

            dim_style = dict(fontsize=5, color="#CC4444", fontweight="bold",
                             ha="center", va="center",
                             bbox=dict(boxstyle="round,pad=0.1", facecolor="white",
                                       edgecolor="none", alpha=0.8))

            # Rear yard (top gap)
            rear_gap = lot_maxy - bp_maxy
            if rear_gap > 1:
                mid_x = (bp_minx + bp_maxx) / 2
                ax.annotate("", xy=(mid_x, lot_maxy), xytext=(mid_x, bp_maxy),
                            arrowprops=dict(arrowstyle="<->", color="#CC4444", lw=0.8))
                ax.text(mid_x, (lot_maxy + bp_maxy) / 2,
                        f"Rear: {rear_gap:.0f}'", **dim_style)

            # Front yard (bottom gap)
            front_gap = bp_miny - lot_miny
            if front_gap > 1:
                mid_x = (bp_minx + bp_maxx) / 2
                ax.annotate("", xy=(mid_x, lot_miny), xytext=(mid_x, bp_miny),
                            arrowprops=dict(arrowstyle="<->", color="#CC4444", lw=0.8))
                ax.text(mid_x, (lot_miny + bp_miny) / 2,
                        f"Front: {front_gap:.0f}'", **dim_style)

            # Side yards (left/right gaps)
            left_gap = bp_minx - lot_minx
            if left_gap > 1:
                mid_y = (bp_miny + bp_maxy) / 2
                ax.annotate("", xy=(lot_minx, mid_y), xytext=(bp_minx, mid_y),
                            arrowprops=dict(arrowstyle="<->", color="#CC4444", lw=0.8))
                ax.text((lot_minx + bp_minx) / 2, mid_y,
                        f"{left_gap:.0f}'", **dim_style)
            right_gap = lot_maxx - bp_maxx
            if right_gap > 1:
                mid_y = (bp_miny + bp_maxy) / 2
                ax.annotate("", xy=(lot_maxx, mid_y), xytext=(bp_maxx, mid_y),
                            arrowprops=dict(arrowstyle="<->", color="#CC4444", lw=0.8))
                ax.text((lot_maxx + bp_maxx) / 2, mid_y,
                        f"{right_gap:.0f}'", **dim_style)

    # ── Group floors by unique footprint shapes ──
    # Floors with the same footprint get grouped (e.g., floors 1-3 same, 4-5 setback)
    floor_groups: list[dict] = []
    for floor in sorted(floors, key=lambda f: f.get("floor_num", f.get("floor", 0))):
        fp = floor.get("footprint", [])
        if len(fp) < 3:
            continue
        fp_key = tuple(tuple(round(c, 1) for c in p) for p in fp)
        floor_num = floor.get("floor_num", floor.get("floor", 0))
        use = floor.get("use", "residential")
        color = floor.get("color", USE_COLORS.get(use, "#CCCCCC"))
        area = floor.get("gross_area_sf", floor.get("plate_area_sf", 0))

        # Check if same footprint as previous group
        if floor_groups and floor_groups[-1]["fp_key"] == fp_key:
            floor_groups[-1]["floor_nums"].append(floor_num)
        else:
            floor_groups.append({
                "fp_key": fp_key,
                "footprint": fp,
                "floor_nums": [floor_num],
                "use": use,
                "color": color,
                "area": area,
            })

    # ── Draw floor plate outlines (outermost first for proper layering) ──
    # Sort by area descending so largest plates are drawn first
    floor_groups_sorted = sorted(floor_groups, key=lambda g: g["area"], reverse=True)

    for i, group in enumerate(floor_groups_sorted):
        fp = group["footprint"]
        fp_arr = np.array(fp + [fp[0]])
        rgb = _hex_to_rgb(group["color"])
        floor_nums = group["floor_nums"]

        # Fill with semi-transparent color (more opaque for upper floors)
        alpha = 0.15 + (i * 0.08)
        alpha = min(alpha, 0.5)
        ax.fill(fp_arr[:, 0], fp_arr[:, 1], alpha=alpha, color=rgb)
        ax.plot(fp_arr[:, 0], fp_arr[:, 1],
                color=rgb, linewidth=1.5 - (i * 0.2), linestyle="-")

        # Label with floor range and area
        centroid_x = np.mean(fp_arr[:-1, 0])
        centroid_y = np.mean(fp_arr[:-1, 1])

        if len(floor_nums) == 1:
            floor_label = f"F{floor_nums[0]}"
        elif floor_nums[-1] - floor_nums[0] == len(floor_nums) - 1:
            floor_label = f"F{floor_nums[0]}-{floor_nums[-1]}"
        else:
            floor_label = f"F{','.join(str(n) for n in floor_nums)}"

        area_label = f"{group['area']:,.0f} SF" if group["area"] else ""
        use_label = USE_LABELS.get(group["use"], group["use"].title())
        label_text = f"{floor_label}\n{use_label}\n{area_label}"

        ax.text(centroid_x, centroid_y, label_text,
                fontsize=6, ha="center", va="center",
                fontweight="bold", color="#1a1a2e",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                         edgecolor="#cccccc", alpha=0.85))

    # ── North arrow ──
    all_x = []
    all_y = []
    for f in floors:
        for pt in f.get("footprint", []):
            all_x.append(pt[0])
            all_y.append(pt[1])
    for pt in lot_poly:
        all_x.append(pt[0])
        all_y.append(pt[1])

    if all_x and all_y:
        arrow_x = max(all_x) + (max(all_x) - min(all_x)) * 0.12
        arrow_y = max(all_y) - (max(all_y) - min(all_y)) * 0.1
        arrow_len = (max(all_y) - min(all_y)) * 0.12
        ax.annotate("N", xy=(arrow_x, arrow_y + arrow_len),
                    fontsize=8, fontweight="bold", ha="center", va="bottom",
                    color="#333333")
        ax.annotate("", xy=(arrow_x, arrow_y + arrow_len),
                    xytext=(arrow_x, arrow_y),
                    arrowprops=dict(arrowstyle="->", color="#333333", lw=1.5))

    # ── Title ──
    title = f"{scenario_name} — Plan View" if scenario_name else "Plan View"
    ax.set_title(title, fontsize=10, fontweight="bold", color="#1a1a2e", pad=8)

    # ── Clean up ──
    ax.tick_params(labelsize=6, colors="#999999")
    ax.set_xlabel("feet", fontsize=7, color="#999999")
    ax.set_ylabel("feet", fontsize=7, color="#999999")
    ax.grid(False)  # Remove grid per user request

    # Show buildable footprint area
    bp_area = massing_model.get("buildable_footprint", {}).get("area_sf", 0)
    lot_area_sf = massing_model.get("lot", {}).get("area_sf", 0)
    if bp_area and lot_area_sf:
        coverage_pct = bp_area / lot_area_sf * 100 if lot_area_sf else 0
        area_text = f"Buildable: {bp_area:,.0f} SF ({coverage_pct:.0f}% coverage)"
    elif bp_area:
        area_text = f"Buildable: {bp_area:,.0f} SF"
    else:
        area_text = ""
    if area_text:
        ax.text(0.02, 0.02, area_text,
                fontsize=6, color="#2C5F8A", fontweight="bold",
                transform=ax.transAxes,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                         edgecolor="#4A90D9", alpha=0.9))

    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], color="#666666", linestyle="--", linewidth=1.5,
                   label="Lot Boundary"),
        plt.Line2D([0], [0], color="#4A90D9", linestyle="-", linewidth=2.0,
                   label="Buildable Footprint"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=6,
             framealpha=0.9, edgecolor="#cccccc")

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────

def render_massing_views(
    massing_model: dict,
    scenario_name: str = "",
) -> dict[str, bytes]:
    """Render both perspective and plan views for a massing model.

    Args:
        massing_model: Output from ``build_massing_model()``.
        scenario_name: Scenario title for labeling.

    Returns:
        Dict with keys ``"perspective"`` and ``"plan"``, each containing
        PNG image bytes.  Values may be empty bytes if rendering fails.
    """
    result = {"perspective": b"", "plan": b""}

    try:
        result["perspective"] = render_perspective_view(
            massing_model, scenario_name=scenario_name,
        )
    except Exception as e:
        logger.warning("Perspective rendering failed for '%s': %s", scenario_name, e)

    try:
        result["plan"] = render_plan_view(
            massing_model, scenario_name=scenario_name,
        )
    except Exception as e:
        logger.warning("Plan view rendering failed for '%s': %s", scenario_name, e)

    return result
