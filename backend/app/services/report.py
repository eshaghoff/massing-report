"""
PDF report generator for zoning feasibility analysis.
Uses ReportLab to generate professional reports with Massing Report branding.

Sections:
  1.  Cover Page (with Massing Report branding + satellite thumbnail)
  2.  Property Maps (satellite + street)
  3.  Site Summary (two-column layout)
  4.  Development Characteristics (highlighted callout cards)
  5.  Zoning Overview (with zoning map)
  6.  Calculation Detail (FAR, units, height breakdowns)
  7.  Development Scenarios (investment case studies with key metrics)
  8.  Scenario Comparison Table
  9.  Parking Analysis
  10. Assemblage Analysis (if applicable)
  11. Disclaimers & Limitations
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    HRFlowable, KeepTogether, Image as RLImage,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.models.schemas import CalculationResult, DevelopmentScenario

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "output")

# ── Institutional Palette (charcoal / off-white / deep blue / muted gold) ──
BLUE = colors.HexColor('#1C3D5A')           # Deep blue (primary)
BLUE_DARK = colors.HexColor('#152D42')      # Darker blue (headers)
DARK = colors.HexColor('#2D2D2D')            # Charcoal text
GREY = colors.HexColor('#7A7A7A')            # Secondary text
LIGHT_BG = colors.HexColor('#F7F6F3')        # Off-white / warm grey
GRID_COLOR = colors.HexColor('#DCDAD5')      # Subtle warm dividers
GREEN_BG = colors.HexColor('#EDF3ED')        # Muted green highlight
HIGHLIGHT_BORDER = colors.HexColor('#1C3D5A')  # Accent borders
FEATURE_BG = colors.HexColor('#F5F4F1')      # Warm off-white cards
GOLD = colors.HexColor('#B8976A')            # Muted gold accent
GOLD_LIGHT = colors.HexColor('#F5F0E8')      # Light warm tone
BADGE_BLUE = colors.HexColor('#E8EDF2')      # Cool badge bg
BADGE_GREEN = colors.HexColor('#E8F0E8')     # Muted green badge
WHITE = colors.white
OFF_WHITE = colors.HexColor('#FAFAF8')       # Paper-white

PAGE_W, PAGE_H = letter
MARGIN = 0.85 * inch
CONTENT_W = PAGE_W - 2 * MARGIN  # ~490 pt ≈ 6.8 inches


# ──────────────────────────────────────────────────────────────────
# LOGO & HEADER / FOOTER (drawn on canvas)
# ──────────────────────────────────────────────────────────────────

def _draw_logo(canvas, x, y, size="small"):
    """Draw the Massing Report logo on the canvas — refined minimal.

    *x, y* is the left-centre of the gold circle.
    """
    canvas.saveState()
    if size == "large":
        r, fs, ls, gap = 16, 12, 13, 20
    else:
        r, fs, ls, gap = 9, 7, 8.5, 12

    # Muted gold circle
    canvas.setFillColor(GOLD)
    canvas.circle(x + r, y, r, fill=1, stroke=0)

    # "MR" inside circle
    canvas.setFillColor(WHITE)
    canvas.setFont('Helvetica-Bold', fs)
    canvas.drawCentredString(x + r, y - fs * 0.35, "MR")

    # Company name — refined spacing
    canvas.setFillColor(DARK)
    canvas.setFont('Helvetica', ls)
    canvas.drawString(x + r * 2 + gap * 0.5, y - ls * 0.35, "MASSING REPORT")
    canvas.restoreState()


def _header_footer_first(canvas, doc):
    """Cover page — logo + thin rule; no page number."""
    canvas.saveState()
    _draw_logo(canvas, doc.leftMargin, PAGE_H - 38, size="small")
    canvas.setStrokeColor(GRID_COLOR)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, PAGE_H - 52, PAGE_W - doc.rightMargin, PAGE_H - 52)
    canvas.restoreState()


def _header_footer_later(canvas, doc):
    """Subsequent pages — minimal header and footer."""
    canvas.saveState()

    # ── Header — thin single rule ──
    _draw_logo(canvas, doc.leftMargin, PAGE_H - 38, size="small")
    canvas.setFillColor(GREY)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawRightString(PAGE_W - doc.rightMargin, PAGE_H - 41,
                           "Zoning Feasibility Analysis")
    canvas.setStrokeColor(GRID_COLOR)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, PAGE_H - 52, PAGE_W - doc.rightMargin, PAGE_H - 52)

    # ── Footer — light grey, minimal ──
    canvas.setStrokeColor(GRID_COLOR)
    canvas.setLineWidth(0.25)
    canvas.line(doc.leftMargin, 40, PAGE_W - doc.rightMargin, 40)
    canvas.setFillColor(colors.HexColor('#AAAAAA'))
    canvas.setFont('Helvetica', 7)
    canvas.drawString(doc.leftMargin, 28,
                      datetime.now().strftime('%B %d, %Y'))
    canvas.drawRightString(PAGE_W - doc.rightMargin, 28, f"{doc.page}")
    canvas.restoreState()


# ──────────────────────────────────────────────────────────────────
# STYLES
# ──────────────────────────────────────────────────────────────────

def _get_styles():
    """Build all report paragraph styles — institutional typography."""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='ReportTitle', fontSize=30, fontName='Helvetica-Bold',
        spaceAfter=6, textColor=DARK, alignment=TA_CENTER,
        leading=36,
    ))
    styles.add(ParagraphStyle(
        name='Subtitle', fontSize=11, fontName='Helvetica',
        alignment=TA_CENTER, textColor=GREY, leading=14,
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle', fontSize=18, fontName='Helvetica-Bold',
        spaceAfter=10, spaceBefore=20, textColor=DARK,
    ))
    styles.add(ParagraphStyle(
        name='SectionHeaderWhite', fontSize=18, fontName='Helvetica-Bold',
        textColor=DARK, leading=24,
    ))
    styles.add(ParagraphStyle(
        name='SubSection', fontSize=11, fontName='Helvetica-Bold',
        spaceAfter=5, spaceBefore=10, textColor=DARK,
    ))
    styles.add(ParagraphStyle(
        name='Body', fontSize=10.5, fontName='Helvetica',
        spaceAfter=5, leading=15, textColor=DARK,
    ))
    styles.add(ParagraphStyle(
        name='SmallBody', fontSize=9.5, fontName='Helvetica',
        spaceAfter=3, leading=13, textColor=DARK,
    ))
    styles.add(ParagraphStyle(
        name='Disclaimer', fontSize=7.5, fontName='Helvetica',
        textColor=colors.HexColor('#999999'), alignment=TA_CENTER, leading=10,
    ))
    styles.add(ParagraphStyle(
        name='NoteText', fontSize=8, fontName='Helvetica',
        textColor=GREY, spaceAfter=3, leading=11,
    ))
    styles.add(ParagraphStyle(
        name='CalloutLabel', fontSize=9, fontName='Helvetica-Bold',
        textColor=DARK, spaceAfter=1, leading=12,
    ))
    styles.add(ParagraphStyle(
        name='CalloutValue', fontSize=9, fontName='Helvetica',
        textColor=GREY, spaceAfter=2, leading=12,
    ))
    styles.add(ParagraphStyle(
        name='BigNumber', fontSize=26, fontName='Helvetica-Bold',
        textColor=BLUE, alignment=TA_CENTER, spaceAfter=2, leading=30,
    ))
    styles.add(ParagraphStyle(
        name='SubSectionItalic', fontSize=10, fontName='Helvetica',
        spaceAfter=4, spaceBefore=6, textColor=GREY,
    ))
    # New styles for institutional design
    styles.add(ParagraphStyle(
        name='MetricNumber', fontSize=24, fontName='Helvetica-Bold',
        textColor=BLUE, alignment=TA_CENTER, leading=28, spaceAfter=0,
    ))
    styles.add(ParagraphStyle(
        name='MetricLabel', fontSize=8, fontName='Helvetica',
        textColor=GREY, alignment=TA_CENTER, leading=10, spaceAfter=0,
    ))
    styles.add(ParagraphStyle(
        name='ExecutiveSummary', fontSize=10, fontName='Helvetica-Oblique',
        textColor=GREY, leading=14, spaceAfter=6, spaceBefore=4,
    ))
    return styles


# ──────────────────────────────────────────────────────────────────
# TABLE, IMAGE & SECTION HELPERS
# ──────────────────────────────────────────────────────────────────

def _section_header(text, section_num=None, styles=None):
    """Section header — thin rule beneath, no heavy bar. Architectural minimal."""
    label = text  # Drop numbering for cleaner look
    sty = (styles or {}).get('SectionHeaderWhite') or ParagraphStyle(
        'SHW', fontSize=18, fontName='Helvetica-Bold', textColor=DARK, leading=24,
    )
    p = Paragraph(label, sty)
    t = Table([[p]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), WHITE),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('LINEBELOW', (0, 0), (-1, -1), 1, BLUE),
    ]))
    return t


def _make_kv_table(data: list[list[str]], col_widths=None) -> Table:
    """Key-value table — subtle row shading, no heavy borders."""
    if col_widths is None:
        col_widths = [2.2 * inch, 4.3 * inch]
    t = Table(data, colWidths=col_widths)
    style_cmds = [
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), DARK),
        ('TEXTCOLOR', (1, 0), (-1, -1), colors.HexColor('#444444')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -2), 0.25, GRID_COLOR),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, GRID_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]
    for i in range(len(data)):
        if i % 2 == 1:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), LIGHT_BG))
    t.setStyle(TableStyle(style_cmds))
    return t


def _make_data_table(data: list[list[str]], col_widths=None) -> Table:
    """Data table — subtle header, thin rules, no heavy grid."""
    if col_widths is None:
        ncols = len(data[0]) if data else 1
        w = CONTENT_W / ncols
        col_widths = [w] * ncols
    t = Table(data, colWidths=col_widths)
    style_cmds = [
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, BLUE),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 1), (-1, -2), 0.25, GRID_COLOR),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, GRID_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), LIGHT_BG))
    t.setStyle(TableStyle(style_cmds))
    return t


def _image_from_bytes(image_bytes: bytes, width: float, height: float) -> RLImage:
    """Convert raw PNG/JPEG bytes to a ReportLab Image flowable."""
    buf = BytesIO(image_bytes)
    return RLImage(buf, width=width, height=height)


def _enhance_satellite_image(image_bytes: bytes, lot_geometry=None) -> bytes:
    """Enhance satellite image for institutional presentation.

    - Desaturate and darken for professional tone
    - Draw lot boundary outline (thin white line) if geometry available
    - Add north arrow (upper-right)
    - Add scale indicator (lower-right)
    - Add subtle vignette/shadow at edges
    """
    try:
        from PIL import Image as PILImage, ImageEnhance, ImageDraw, ImageFont
        from io import BytesIO as PILBuf

        pil_img = PILImage.open(PILBuf(image_bytes))
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        w, h = pil_img.size

        # Desaturate + darken
        enhancer = ImageEnhance.Color(pil_img)
        pil_img = enhancer.enhance(0.6)
        enhancer = ImageEnhance.Brightness(pil_img)
        pil_img = enhancer.enhance(0.82)

        draw = ImageDraw.Draw(pil_img)

        # ── Lot boundary outline ──
        if lot_geometry:
            try:
                coords = None
                if isinstance(lot_geometry, dict):
                    coords = lot_geometry.get('coordinates', [])
                    if lot_geometry.get('type') == 'MultiPolygon':
                        # Flatten MultiPolygon to first polygon's outer ring
                        if coords and coords[0]:
                            coords = coords[0][0]
                    elif lot_geometry.get('type') == 'Polygon':
                        if coords:
                            coords = coords[0]
                elif hasattr(lot_geometry, 'coordinates'):
                    coords = lot_geometry.coordinates
                    if hasattr(lot_geometry, 'type'):
                        if lot_geometry.type == 'MultiPolygon':
                            coords = coords[0][0] if coords and coords[0] else None
                        elif lot_geometry.type == 'Polygon':
                            coords = coords[0] if coords else None

                if coords and len(coords) >= 3:
                    # Map geo coords to pixel coords
                    lngs = [c[0] for c in coords]
                    lats = [c[1] for c in coords]
                    min_lng, max_lng = min(lngs), max(lngs)
                    min_lat, max_lat = min(lats), max(lats)
                    # Add padding
                    pad = 0.15
                    lng_range = max_lng - min_lng or 0.0001
                    lat_range = max_lat - min_lat or 0.0001
                    pixels = []
                    for lng, lat in coords:
                        px = pad * w + (1 - 2 * pad) * w * (lng - min_lng) / lng_range
                        py = pad * h + (1 - 2 * pad) * h * (1 - (lat - min_lat) / lat_range)
                        pixels.append((px, py))
                    # Draw boundary outline — thin white with slight glow
                    for width_px, color in [(4, (255, 255, 255, 60)), (2, (255, 255, 255, 180))]:
                        pil_img_rgba = pil_img.convert('RGBA')
                        overlay = PILImage.new('RGBA', pil_img_rgba.size, (0, 0, 0, 0))
                        overlay_draw = ImageDraw.Draw(overlay)
                        overlay_draw.line(pixels + [pixels[0]], fill=color, width=width_px)
                        pil_img = PILImage.alpha_composite(pil_img_rgba, overlay).convert('RGB')
                        draw = ImageDraw.Draw(pil_img)
            except Exception:
                pass  # Geometry parsing failed, skip boundary

        # ── North arrow (upper-right corner) ──
        arrow_x = w - 45
        arrow_y = 20
        arrow_len = 30
        # Stem
        draw.line([(arrow_x, arrow_y + arrow_len), (arrow_x, arrow_y + 4)],
                  fill=(255, 255, 255), width=2)
        # Arrowhead
        draw.polygon([(arrow_x, arrow_y), (arrow_x - 6, arrow_y + 10),
                       (arrow_x + 6, arrow_y + 10)],
                      fill=(255, 255, 255))
        # "N" label
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except Exception:
            font = ImageFont.load_default()
        draw.text((arrow_x - 4, arrow_y + arrow_len + 2), "N",
                  fill=(255, 255, 255), font=font)

        # ── Scale bar (lower-right) ──
        bar_len = 80
        bar_y = h - 25
        bar_x = w - bar_len - 20
        draw.rectangle([(bar_x, bar_y), (bar_x + bar_len, bar_y + 4)],
                        fill=(255, 255, 255))
        draw.line([(bar_x, bar_y - 3), (bar_x, bar_y + 7)],
                  fill=(255, 255, 255), width=1)
        draw.line([(bar_x + bar_len, bar_y - 3), (bar_x + bar_len, bar_y + 7)],
                  fill=(255, 255, 255), width=1)
        try:
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 9)
        except Exception:
            small_font = ImageFont.load_default()
        draw.text((bar_x + bar_len // 2 - 10, bar_y + 6), "~100 ft",
                  fill=(255, 255, 255), font=small_font)

        buf = PILBuf()
        pil_img.save(buf, format='JPEG', quality=92)
        return buf.getvalue()
    except Exception:
        return image_bytes


def _make_feature_card(label: str, value: str, detail: str = "") -> str:
    """Build HTML content for a single feature callout card."""
    cell = f"<b>{label}</b><br/>{value}"
    if detail:
        cell += f"<br/><font size='7' color='#999999'>{detail}</font>"
    return cell


# ──────────────────────────────────────────────────────────────────
# SECTION 1: COVER PAGE
# ──────────────────────────────────────────────────────────────────

def _build_cover_page(story, styles, lot, env, report_id, map_images=None):
    """Cover page — boutique development firm aesthetic."""
    story.append(Spacer(1, 10))

    # ── Full-width satellite photo with professional enhancements ──
    if map_images and map_images.get("satellite_bytes"):
        try:
            lot_geom = getattr(lot, 'geometry', None)
            sat_bytes = _enhance_satellite_image(
                map_images["satellite_bytes"], lot_geometry=lot_geom)
            img = _image_from_bytes(sat_bytes, CONTENT_W, 3.0 * inch)
            story.append(img)
            story.append(Spacer(1, 14))
        except Exception:
            if map_images.get("satellite_bytes"):
                img = _image_from_bytes(map_images["satellite_bytes"], CONTENT_W, 3.0 * inch)
                story.append(img)
                story.append(Spacer(1, 14))

    # ── Title block — large, centered, clean ──
    addr_text = lot.address or "Address Not Available"
    # Title case instead of ALL CAPS
    addr_display = addr_text.title() if addr_text == addr_text.upper() else addr_text
    story.append(Paragraph(
        f"{addr_display}",
        ParagraphStyle('CoverTitle', fontSize=28, fontName='Helvetica-Bold',
                       textColor=DARK, alignment=TA_CENTER, leading=34),
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Zoning Feasibility Analysis",
        ParagraphStyle('CoverSubtitle', fontSize=13, fontName='Helvetica',
                       textColor=GREY, alignment=TA_CENTER, leading=16),
    ))
    story.append(Spacer(1, 10))

    # ── Thin gold rule ──
    story.append(HRFlowable(width="30%", thickness=1, color=GOLD, hAlign='CENTER',
                             spaceAfter=14))

    # ── Horizontal info bar — key facts in one row ──
    neighbourhood = getattr(lot, 'neighbourhood', None) or ""
    zoning = ", ".join(lot.zoning_districts) if lot.zoning_districts else "N/A"
    lot_area = f"{lot.lot_area:,.0f} SF" if lot.lot_area else "N/A"

    info_style = ParagraphStyle('InfoBar', fontSize=8.5, fontName='Helvetica',
                                textColor=GREY, alignment=TA_CENTER, leading=11)
    info_bold = ParagraphStyle('InfoBarBold', fontSize=8.5, fontName='Helvetica-Bold',
                               textColor=DARK, alignment=TA_CENTER, leading=11)

    info_cells = [
        [Paragraph("BBL", info_style), Paragraph("Zoning", info_style),
         Paragraph("Lot Area", info_style), Paragraph("Borough", info_style)],
        [Paragraph(_format_bbl(lot.bbl), info_bold), Paragraph(zoning, info_bold),
         Paragraph(lot_area, info_bold), Paragraph(_borough_name(lot.borough), info_bold)],
    ]

    if neighbourhood:
        info_cells[0].append(Paragraph("Neighborhood", info_style))
        info_cells[1].append(Paragraph(neighbourhood, info_bold))

    ncols = len(info_cells[0])
    col_w = CONTENT_W / ncols
    info_t = Table(info_cells, colWidths=[col_w] * ncols)
    info_t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 1), (-1, 1), 2),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 0, WHITE),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, GRID_COLOR),
        ('LINEBELOW', (0, 1), (-1, 1), 0.5, GRID_COLOR),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
    ]))
    story.append(info_t)
    story.append(Spacer(1, 18))

    # ── Cross streets + lot details ──
    cross_streets = getattr(lot, 'cross_streets', None) or ""
    detail_items = []
    if cross_streets:
        detail_items.append(f"Cross Streets: {cross_streets}")
    detail_items.append(f"Lot Type: {lot.lot_type.capitalize()}")
    if lot.street_width:
        detail_items.append(f"Street Width: {lot.street_width.capitalize()}")

    detail_text = "  \u2022  ".join(detail_items)
    story.append(Paragraph(
        detail_text,
        ParagraphStyle('CoverDetails', fontSize=9, fontName='Helvetica',
                       textColor=GREY, alignment=TA_CENTER, leading=12),
    ))
    story.append(Spacer(1, 24))

    # ── Minimal footer ──
    footer_html = (
        f'<font color="#AAAAAA" size="7.5">'
        f'{datetime.now().strftime("%B %d, %Y")}  \u2022  Report ID: {report_id}'
        f'</font>'
    )
    story.append(Paragraph(footer_html, ParagraphStyle(
        'CoverFooter', fontSize=7.5, alignment=TA_CENTER, textColor=GREY,
    )))
    story.append(PageBreak())


# ──────────────────────────────────────────────────────────────────
# SECTION 2: PROPERTY MAPS
# ──────────────────────────────────────────────────────────────────

def _build_property_maps(story, styles, lot, map_images):
    """Section 2: NYC overview map + close-up street map (no satellite — it's on cover)."""
    has_street = map_images and map_images.get("street_bytes")
    has_city = map_images and map_images.get("city_overview_bytes")
    has_context = map_images and map_images.get("context_map_bytes")
    has_geometry = lot.geometry is not None

    if not has_street and not has_city and not has_context and not has_geometry:
        return

    story.append(_section_header("Property Location", section_num=2, styles=styles))
    story.append(Spacer(1, 8))

    # Try side-by-side layout: NYC overview (left) + close-up street (right)
    left_img = None
    right_img = None

    # Left: NYC overview or context map
    if has_city:
        try:
            left_img = _image_from_bytes(map_images["city_overview_bytes"], 3.3 * inch, 2.8 * inch)
        except Exception:
            pass
    if not left_img and has_context:
        try:
            left_img = _image_from_bytes(map_images["context_map_bytes"], 3.3 * inch, 2.8 * inch)
        except Exception:
            pass

    # Right: close-up street map
    if has_street:
        try:
            right_img = _image_from_bytes(map_images["street_bytes"], 3.3 * inch, 2.8 * inch)
        except Exception:
            pass

    if left_img and right_img:
        # Side-by-side layout
        left_cell = [
            [Paragraph("NYC Overview", ParagraphStyle(
                'MapLabel', fontSize=9, fontName='Helvetica-Bold',
                textColor=BLUE_DARK, alignment=TA_CENTER, spaceAfter=4))],
            [left_img],
            [Paragraph(
                "Red marker indicates subject property. Source: ESRI.",
                ParagraphStyle('MapNote', fontSize=7, fontName='Helvetica-Oblique',
                               textColor=GREY, alignment=TA_CENTER, spaceBefore=2))],
        ]
        right_cell = [
            [Paragraph("Property Close-Up", ParagraphStyle(
                'MapLabel2', fontSize=9, fontName='Helvetica-Bold',
                textColor=BLUE_DARK, alignment=TA_CENTER, spaceAfter=4))],
            [right_img],
            [Paragraph(
                "Lot boundary outlined in blue. Source: ESRI / OpenStreetMap.",
                ParagraphStyle('MapNote2', fontSize=7, fontName='Helvetica-Oblique',
                               textColor=GREY, alignment=TA_CENTER, spaceBefore=2))],
        ]
        left_t = Table(left_cell, colWidths=[3.3 * inch])
        right_t = Table(right_cell, colWidths=[3.3 * inch])
        for t in (left_t, right_t):
            t.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))

        pair = Table([[left_t, right_t]], colWidths=[CONTENT_W / 2, CONTENT_W / 2])
        pair.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(pair)
        story.append(Spacer(1, 10))
    else:
        # Fallback: stack whatever we have
        if left_img:
            story.append(Paragraph("NYC Overview", styles['SubSection']))
            story.append(left_img)
            story.append(Paragraph(
                "Red marker indicates subject property. Source: ESRI.",
                styles['NoteText'],
            ))
            story.append(Spacer(1, 8))
        if right_img:
            story.append(Paragraph("Street Map with Lot Boundary", styles['SubSection']))
            story.append(right_img)
            story.append(Paragraph(
                "Lot boundary outlined in blue. Source: ESRI / OpenStreetMap.",
                styles['NoteText'],
            ))
            story.append(Spacer(1, 8))

    # If we still have the context map and it wasn't used above, show it
    if has_context and not has_city and left_img is None:
        try:
            story.append(Paragraph("Neighbourhood Context", styles['SubSection']))
            ctx_img = _image_from_bytes(map_images["context_map_bytes"], CONTENT_W, 3.0 * inch)
            story.append(ctx_img)
            story.append(Paragraph(
                "Zoomed-out view showing property location. Source: ESRI.",
                styles['NoteText'],
            ))
            story.append(Spacer(1, 8))
        except Exception:
            pass

    # Fallback: programmatic lot diagram
    if not has_street and not has_city and not has_context and has_geometry:
        story.append(Paragraph("Lot Boundary Diagram", styles['SubSection']))
        try:
            from app.services.maps import draw_lot_diagram_reportlab
            env_rear = getattr(lot, '_env_rear_yard', 30)
            env_front = getattr(lot, '_env_front_yard', 0)
            drawing = draw_lot_diagram_reportlab(
                geometry=lot.geometry,
                lot_area=lot.lot_area,
                lot_frontage=lot.lot_frontage,
                lot_depth=lot.lot_depth,
                rear_yard=env_rear,
                front_yard=env_front,
            )
            story.append(drawing)
            story.append(Paragraph(
                "Programmatic rendering from lot geometry data.",
                styles['NoteText'],
            ))
        except Exception:
            story.append(Paragraph(
                "Map images not available. Lot geometry on file.",
                styles['Body'],
            ))

    story.append(PageBreak())


# ──────────────────────────────────────────────────────────────────
# SECTION 3: SITE SUMMARY  (two-column layout, no dimensions, no $)
# ──────────────────────────────────────────────────────────────────

def _build_site_summary(story, styles, lot, env):
    """Section 3: Two-column site information — property info left, PLUTO data right."""
    story.append(_section_header("Site Summary", section_num=3, styles=styles))
    story.append(Spacer(1, 6))

    # ── Left column data (property) ──
    left_rows = [
        ["Address", lot.address or "N/A"],
        ["BBL", _format_bbl(lot.bbl)],
        ["Borough", _borough_name(lot.borough)],
        ["Lot Area", f"{lot.lot_area:,.0f} SF" if lot.lot_area else "N/A"],
        ["Lot Type", lot.lot_type.capitalize()],
        ["Street Width", f"{lot.street_width.capitalize()} street"],
        ["Split Zone", "Yes" if lot.split_zone else "No"],
    ]

    # ── Right column data (PLUTO / existing conditions) ──
    right_rows = []
    if lot.pluto:
        if lot.pluto.cd:
            right_rows.append(["Community District", str(lot.pluto.cd)])
        if lot.pluto.zipcode:
            right_rows.append(["ZIP Code", lot.pluto.zipcode])
        if lot.pluto.yearbuilt:
            right_rows.append(["Year Built", str(lot.pluto.yearbuilt)])
        if lot.pluto.builtfar:
            right_rows.append(["Existing FAR", f"{lot.pluto.builtfar:.2f}"])
        if lot.pluto.numfloors:
            right_rows.append(["Existing Floors", f"{lot.pluto.numfloors:.0f}"])
        if lot.pluto.bldgarea:
            right_rows.append(["Existing Bldg Area", f"{lot.pluto.bldgarea:,.0f} SF"])
        if lot.pluto.landuse:
            right_rows.append(["Current Land Use", _land_use_desc(lot.pluto.landuse)])

    # If no PLUTO data, fall back to single-column
    if not right_rows:
        story.append(_make_kv_table(left_rows))
        story.append(Spacer(1, 8))
        return

    # Build two side-by-side KV sub-tables
    col_half = CONTENT_W / 2 - 4
    kv_w = [1.4 * inch, col_half - 1.4 * inch]

    left_table = _make_kv_table(left_rows, col_widths=kv_w)
    right_table = _make_kv_table(right_rows, col_widths=kv_w)

    # Left header
    lh = Paragraph("<b>Property Information</b>", ParagraphStyle(
        'ColHead', fontSize=9, fontName='Helvetica-Bold', textColor=BLUE_DARK,
    ))
    rh = Paragraph("<b>Existing Conditions (PLUTO)</b>", ParagraphStyle(
        'ColHead', fontSize=9, fontName='Helvetica-Bold', textColor=BLUE_DARK,
    ))

    outer_data = [
        [lh, rh],
        [left_table, right_table],
    ]
    outer = Table(outer_data, colWidths=[col_half, col_half])
    outer.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(outer)
    story.append(Spacer(1, 8))


# ──────────────────────────────────────────────────────────────────
# SECTION 4: KEY DEVELOPMENT FEATURES
# ──────────────────────────────────────────────────────────────────

def _build_highlighted_features(story, styles, lot, env, scenarios=None):
    """Section 4: Visual callout cards highlighting key development features."""
    story.append(_section_header("Development Characteristics", section_num=4, styles=styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Key zoning and site characteristics relevant to this development analysis:",
        styles['Body'],
    ))
    story.append(Spacer(1, 4))

    features = []

    # Zoning district
    district = lot.zoning_districts[0] if lot.zoning_districts else "N/A"
    features.append(("Zoning District", district, _zoning_district_desc(district)))

    # Street width
    if lot.street_width == "wide":
        sw_detail = "Wide street (75'+ mapped width) \u2014 higher FAR and height limits may apply"
    else:
        sw_detail = "Narrow street (<75' mapped width) \u2014 contextual height limits apply"
    features.append(("Street Classification", f"{lot.street_width.capitalize()} Street", sw_detail))

    # Quality Housing vs Height Factor
    if env.quality_housing:
        features.append(("Building Program", "Quality Housing",
                         "Contextual envelope with base height, setback, and max height limits"))
    elif env.height_factor:
        features.append(("Building Program", "Height Factor",
                         "Non-contextual envelope \u2014 no height cap, sky exposure plane controls massing"))

    # Lot type
    lot_type_details = {
        "corner": "Corner lot \u2014 different height/setback rules, potential wide street frontage",
        "through": "Through lot \u2014 rear yard equivalent rules (ZR 23-532), more flexible envelope",
        "interior": "Interior lot \u2014 standard front/rear/side yard requirements",
        "irregular": "Irregular lot shape \u2014 buildable footprint may be constrained",
    }
    features.append(("Lot Type", lot.lot_type.capitalize(),
                     lot_type_details.get(lot.lot_type, "")))

    # Parking waiver
    if scenarios:
        waiver = any(s.parking and s.parking.waiver_eligible for s in scenarios)
        no_parking = all(
            (not s.parking or s.parking.total_spaces_required == 0) for s in scenarios
        )
        if no_parking:
            features.append(("Parking", "No Parking Required",
                             "Transit zone location or small building exemption"))
        elif waiver:
            features.append(("Parking", "Waiver Eligible",
                             "Small building parking waiver may eliminate parking requirement"))

    # MIH
    if lot.is_mih_area:
        features.append(("MIH Designation", lot.mih_option or "Yes",
                         "Mandatory Inclusionary Housing \u2014 bonus FAR with affordability requirement"))

    # IH Bonus
    if env.ih_bonus_far:
        features.append(("IH Bonus FAR", f"+{env.ih_bonus_far:.2f}",
                         "Additional FAR available through Inclusionary Housing program"))

    # Overlays
    if lot.overlays:
        features.append(("Commercial Overlays", ", ".join(lot.overlays),
                         "Commercial overlay allows ground-floor commercial in residential district"))

    # Special districts
    if lot.special_districts:
        features.append(("Special Districts", ", ".join(lot.special_districts),
                         "Special district rules may modify underlying zoning"))

    # Limited height
    if lot.limited_height:
        features.append(("Limited Height District", lot.limited_height,
                         "Height is further restricted by limited height district designation"))

    # Historic
    if lot.is_historic_district:
        features.append(("Historic District", "Yes",
                         "Landmarks Preservation Commission review required"))

    # Flood/Coastal
    if getattr(lot, 'flood_zone', None):
        features.append(("Flood Zone", lot.flood_zone,
                         "Flood-resistant construction may be required"))
    if getattr(lot, 'coastal_zone', False):
        features.append(("Coastal Zone", "Yes",
                         "Waterfront/coastal regulations may apply"))

    _render_feature_grid(story, styles, features)
    story.append(Spacer(1, 8))


def _render_feature_grid(story, styles, features):
    """Render features as a styled 2-column grid of callout cards."""
    if not features:
        return

    cell_style = ParagraphStyle(
        'FeatureCell', fontSize=9, fontName='Helvetica', leading=12, spaceAfter=2,
    )
    cells = [Paragraph(_make_feature_card(l, v, d), cell_style)
             for l, v, d in features]

    rows = []
    for i in range(0, len(cells), 2):
        if i + 1 < len(cells):
            rows.append([cells[i], cells[i + 1]])
        else:
            rows.append([cells[i], ""])

    col_w = CONTENT_W / 2 - 4
    t = Table(rows, colWidths=[col_w, col_w], spaceBefore=4, spaceAfter=4)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.25, GRID_COLOR),
        ('LINEBEFORE', (1, 0), (1, -1), 0.25, GRID_COLOR),
    ]
    t.setStyle(TableStyle(style_cmds))
    story.append(t)


# ──────────────────────────────────────────────────────────────────
# SECTION 5: ZONING OVERVIEW  (with zoning map)
# ──────────────────────────────────────────────────────────────────

def _build_zoning_overview(story, styles, lot, env, map_images=None):
    """Section 5: Zoning districts, overlays, FAR, height/setback, and optional zoning map."""
    story.append(_section_header("Zoning Overview", section_num=5, styles=styles))
    story.append(Spacer(1, 6))

    # ── Key Metric Data Cards — large bold numbers ──
    metric_cards = []
    lot_area_val = lot.lot_area or 0
    if env.residential_far:
        metric_cards.append(("Residential FAR", f"{env.residential_far:.2f}", "Floor Area Ratio"))
    if env.max_building_height is not None:
        metric_cards.append(("Max Height", f"{env.max_building_height:.0f}'", "Building Height Limit"))
    elif env.height_factor:
        metric_cards.append(("Max Height", "No Cap", "Sky Exposure Plane"))
    if env.residential_far and lot_area_val:
        max_zfa = env.residential_far * lot_area_val
        du_raw = max_zfa / 680
        du_count = int(du_raw) + 1 if du_raw - int(du_raw) >= 0.75 else int(du_raw)
        metric_cards.append(("Max Units", str(du_count), f"Based on {max_zfa:,.0f} SF ZFA"))
    if env.residential_far and lot_area_val:
        max_zfa = env.residential_far * lot_area_val
        metric_cards.append(("Max ZFA", f"{max_zfa:,.0f}", "Zoning Floor Area (SF)"))
    if env.lot_coverage_max is not None:
        metric_cards.append(("Lot Coverage", f"{env.lot_coverage_max:.0f}%", "Maximum Coverage"))

    if metric_cards:
        # Limit to 4 cards for clean layout
        metric_cards = metric_cards[:4]
        ncards = len(metric_cards)
        card_w = CONTENT_W / ncards

        lbl_style = ParagraphStyle('_mcLbl', fontSize=7.5, fontName='Helvetica',
                                    textColor=GREY, alignment=TA_CENTER, leading=9)
        val_style = ParagraphStyle('_mcVal', fontSize=22, fontName='Helvetica-Bold',
                                    textColor=BLUE, alignment=TA_CENTER, leading=26)
        sub_style = ParagraphStyle('_mcSub', fontSize=7, fontName='Helvetica',
                                    textColor=GREY, alignment=TA_CENTER, leading=9)

        row_labels = [Paragraph(t, lbl_style) for t, _, _ in metric_cards]
        row_values = [Paragraph(v, val_style) for _, v, _ in metric_cards]
        row_subs = [Paragraph(s, sub_style) for _, _, s in metric_cards]

        card_t = Table([row_labels, row_values, row_subs],
                       colWidths=[card_w] * ncards)
        style_cmds = [
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 1),
            ('TOPPADDING', (0, 1), (-1, 1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 2),
            ('TOPPADDING', (0, 2), (-1, 2), 1),
            ('BOTTOMPADDING', (0, 2), (-1, 2), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
            ('LINEABOVE', (0, 0), (-1, 0), 2, GOLD),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, GRID_COLOR),
        ]
        for i in range(1, ncards):
            style_cmds.append(('LINEBEFORE', (i, 0), (i, -1), 0.25, GRID_COLOR))
        card_t.setStyle(TableStyle(style_cmds))
        story.append(card_t)
        story.append(Spacer(1, 10))

    # ── Zoning map image (if available) ──
    if map_images and map_images.get("zoning_map_bytes"):
        try:
            story.append(Paragraph("Zoning Map — Subject Property Location", styles['SubSection']))
            img = _image_from_bytes(map_images["zoning_map_bytes"], CONTENT_W, 3.5 * inch)
            story.append(img)
            story.append(Paragraph(
                "Subject property marked in blue. Zoning districts colour-coded. "
                "Source: NYC Dept. of City Planning / ESRI.",
                styles['NoteText'],
            ))
            story.append(Spacer(1, 8))
        except Exception as e:
            logger.warning("Failed to embed zoning map: %s", e)

    # ── Two-column: Districts/Overlays (left) + FAR (right) ──
    zo_col_half = CONTENT_W / 2 - 4
    zo_kv_w = [1.3 * inch, zo_col_half - 1.3 * inch]

    # LEFT: Districts & Overlays
    zoning_info = [
        ["Primary District", lot.zoning_districts[0] if lot.zoning_districts else "N/A"],
    ]
    if len(lot.zoning_districts) > 1:
        zoning_info.append(["Other Districts", ", ".join(lot.zoning_districts[1:])])
    if lot.overlays:
        zoning_info.append(["Overlays", ", ".join(lot.overlays)])
    if lot.special_districts:
        zoning_info.append(["Special Districts", ", ".join(lot.special_districts)])
    if lot.is_mih_area:
        zoning_info.append(["MIH", lot.mih_option or "Yes"])
    if lot.limited_height:
        zoning_info.append(["Ltd. Height", lot.limited_height])
    if lot.is_historic_district:
        zoning_info.append(["Historic", "Yes"])
    if getattr(lot, 'flood_zone', None):
        zoning_info.append(["Flood Zone", lot.flood_zone])
    if getattr(lot, 'coastal_zone', False):
        zoning_info.append(["Coastal Zone", "Yes"])

    zo_left_hdr = Paragraph("<b>Districts &amp; Overlays</b>", ParagraphStyle(
        'ZOhdr1', fontSize=9, fontName='Helvetica-Bold', textColor=BLUE_DARK, spaceAfter=2))
    zo_left_t = _make_kv_table(zoning_info, col_widths=zo_kv_w)

    # RIGHT: FAR table
    far_data = [["Use", "FAR", "Max ZFA"]]
    if env.residential_far:
        far_data.append([
            "Residential", f"{env.residential_far:.2f}",
            f"{env.max_residential_zfa:,.0f} SF" if env.max_residential_zfa else "N/A",
        ])
    if env.commercial_far:
        far_data.append([
            "Commercial", f"{env.commercial_far:.2f}",
            f"{env.max_commercial_zfa:,.0f} SF" if env.max_commercial_zfa else "N/A",
        ])
    if env.cf_far:
        far_data.append([
            "Community Facility", f"{env.cf_far:.2f}",
            f"{env.max_cf_zfa:,.0f} SF" if env.max_cf_zfa else "N/A",
        ])
    if env.ih_bonus_far:
        far_data.append([
            "IH Bonus", f"+{env.ih_bonus_far:.2f}", "Inclusionary Housing bonus",
        ])
    zo_right_hdr = Paragraph("<b>Floor Area Ratio (FAR)</b>", ParagraphStyle(
        'ZOhdr2', fontSize=9, fontName='Helvetica-Bold', textColor=BLUE_DARK, spaceAfter=2))
    far_w = [0.9 * inch, 0.6 * inch, zo_col_half - 1.5 * inch]
    zo_right_t = _make_data_table(far_data, col_widths=far_w) if len(far_data) > 1 else Paragraph("", styles['Body'])

    # Compose Districts + FAR side-by-side
    zo_left_inner = Table([[zo_left_hdr], [zo_left_t]], colWidths=[zo_col_half])
    zo_left_inner.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    zo_right_inner = Table([[zo_right_hdr], [zo_right_t]], colWidths=[zo_col_half])
    zo_right_inner.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    zo_two_col = Table([[zo_left_inner, zo_right_inner]], colWidths=[zo_col_half + 4, zo_col_half + 4])
    zo_two_col.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(zo_two_col)
    story.append(Spacer(1, 6))

    # Height & Setback — full width since it can be complex
    story.append(Paragraph("Height &amp; Setback", styles['SubSection']))
    hs_data = []
    if env.quality_housing:
        hs_data.append(["Program", "Quality Housing (Contextual)"])
    elif env.height_factor:
        hs_data.append(["Program", "Height Factor (Non-Contextual)"])
    if env.base_height_min is not None:
        hs_data.append(["Min Base Height", f"{env.base_height_min} ft"])
    if env.base_height_max is not None:
        hs_data.append(["Max Base Height", f"{env.base_height_max} ft"])
    if env.max_building_height is not None:
        hs_data.append(["Max Bldg Height", f"{env.max_building_height} ft"])
    elif env.height_factor:
        hs_data.append(["Max Bldg Height", "No cap (SEP applies)"])
    hs_data.append(["Rear Yard", f"{env.rear_yard} ft"])
    if env.front_yard > 0:
        hs_data.append(["Front Yard", f"{env.front_yard} ft"])
    hs_data.append(["Side Yards",
                     f"Required ({env.side_yard_width}' each)" if env.side_yards_required
                     else "Not required"])
    if env.lot_coverage_max is not None:
        hs_data.append(["Lot Coverage", f"{env.lot_coverage_max}%"])
    if env.sky_exposure_plane:
        hs_data.append(["Sky Exposure Plane",
            f"Starts {env.sky_exposure_plane.start_height}', "
            f"ratio {env.sky_exposure_plane.ratio}:1"])
    story.append(_make_kv_table(hs_data))
    story.append(Spacer(1, 6))

    # ── Key Zoning Rules Summary ──
    story.append(Paragraph("Key Zoning Rules for This District", styles['SubSection']))
    story.append(Spacer(1, 2))

    district = lot.zoning_districts[0] if lot.zoning_districts else "N/A"
    lot_area = lot.lot_area or 0
    rules = []

    # FAR
    if env.residential_far:
        rules.append(
            f"<b>Residential FAR:</b> {env.residential_far:.2f} "
            f"({env.residential_far * lot_area:,.0f} SF max ZFA)"
        )
    if env.commercial_far:
        rules.append(
            f"<b>Commercial FAR:</b> {env.commercial_far:.2f} "
            f"({env.commercial_far * lot_area:,.0f} SF max ZFA)"
        )
    if env.cf_far:
        rules.append(
            f"<b>Community Facility FAR:</b> {env.cf_far:.2f} "
            f"({env.cf_far * lot_area:,.0f} SF max ZFA)"
        )

    # Lot coverage
    if env.lot_coverage_max is not None:
        coverage_sf = lot_area * env.lot_coverage_max / 100
        rules.append(
            f"<b>Max Lot Coverage:</b> {env.lot_coverage_max:.0f}% "
            f"({coverage_sf:,.0f} SF max building footprint)"
        )
    else:
        rules.append("<b>Max Lot Coverage:</b> No specific limit")

    # Height
    if env.max_building_height is not None:
        rules.append(f"<b>Max Building Height:</b> {env.max_building_height:.0f} ft")
    elif env.height_factor:
        rules.append("<b>Max Building Height:</b> No cap (sky exposure plane applies)")

    # Yards
    yard_parts = []
    if env.rear_yard > 0:
        yard_parts.append(f"rear {env.rear_yard:.0f}'")
    if env.front_yard > 0:
        yard_parts.append(f"front {env.front_yard:.0f}'")
    if env.side_yards_required:
        yard_parts.append(f"side {env.side_yard_width:.0f}' each")
    else:
        yard_parts.append("no side yards")
    rules.append(f"<b>Yard Requirements:</b> {', '.join(yard_parts)}")

    # Parking
    rules.append(
        "<b>Parking:</b> Per ZR Article V — varies by unit count, borough, "
        "and transit zone. Small buildings (\u226410 units) may qualify for waiver."
    )

    # DU Factor
    if env.residential_far and lot_area:
        max_zfa = env.residential_far * lot_area
        raw = max_zfa / 680
        rounded = int(raw) + 1 if raw - int(raw) >= 0.75 else int(raw)
        rules.append(
            f"<b>Dwelling Unit Factor:</b> Max {rounded} units "
            f"(ZR 23-52: ZFA {max_zfa:,.0f} \u00f7 680 = {raw:.2f})"
        )

    # Quality Housing / Height Factor
    if env.quality_housing:
        rules.append(
            "<b>Building Program:</b> Quality Housing \u2014 contextual envelope "
            "with base height, setback above base, and max height limit"
        )
    elif env.height_factor:
        rules.append(
            "<b>Building Program:</b> Height Factor \u2014 no height cap, "
            "sky exposure plane controls upper-floor massing, open space ratio required"
        )

    for rule in rules:
        story.append(Paragraph(f"\u2022 {rule}", styles['SmallBody']))
    story.append(Spacer(1, 8))


# ──────────────────────────────────────────────────────────────────
# SECTION 6: DETAILED CALCULATIONS
# ──────────────────────────────────────────────────────────────────

def _build_calculation_breakdown(story, styles, lot, env):
    """Section 6: Show-your-work calculations in two-column layout."""
    story.append(PageBreak())
    story.append(_section_header("Calculation Detail", section_num=6, styles=styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Step-by-step breakdown of key zoning calculations for this site. "
        "ZFA = FAR \u00d7 Lot Area (gross area minus exemptions).",
        styles['SmallBody'],
    ))
    story.append(Spacer(1, 4))

    lot_area = lot.lot_area or 0
    calc_half = CONTENT_W / 2 - 4
    calc_kv = [1.2 * inch, calc_half - 1.2 * inch]

    # ══════════════════════════════════════════════════════════════
    # LEFT COLUMN: Lot/Footprint + FAR
    # ══════════════════════════════════════════════════════════════
    left_parts = []

    # 6a. Lot & Footprint
    left_parts.append(Paragraph("<b>6a. Lot &amp; Buildable Footprint</b>", ParagraphStyle(
        'C6a', fontSize=9, fontName='Helvetica-Bold', textColor=BLUE_DARK, spaceAfter=2)))
    lot_calc = [["Lot Area", f"{lot_area:,.0f} SF"]]
    rear_yd = getattr(env, 'rear_yard', 0) or 0
    front_yd = getattr(env, 'front_yard', 0) or 0
    side_req = getattr(env, 'side_yards_required', False)
    side_w = getattr(env, 'side_yard_width', 0) or 0
    if rear_yd and lot.lot_frontage:
        lot_calc.append(["Rear Yard", f"{rear_yd * lot.lot_frontage:,.0f} SF ({rear_yd}')"])
    if front_yd and lot.lot_frontage:
        lot_calc.append(["Front Yard", f"{front_yd * lot.lot_frontage:,.0f} SF ({front_yd}')"])
    if side_req and side_w and lot.lot_depth:
        lot_calc.append(["Side Yards", f"{2 * side_w * (lot.lot_depth - rear_yd):,.0f} SF"])
    if lot.lot_frontage and lot.lot_depth:
        eff_w = lot.lot_frontage - (2 * side_w if side_req else 0)
        eff_d = lot.lot_depth - rear_yd - front_yd
        buildable = max(eff_w * eff_d, 0)
        lot_calc.append(["Buildable FP", f"{buildable:,.0f} SF"])
        if env.lot_coverage_max:
            lot_calc.append(["Max Coverage",
                             f"{env.lot_coverage_max}% = {lot_area * env.lot_coverage_max / 100:,.0f} SF"])
    left_parts.append(_make_kv_table(lot_calc, col_widths=calc_kv))

    # 6b. FAR Calculation
    left_parts.append(Paragraph("<b>6b. FAR Breakdown</b>", ParagraphStyle(
        'C6b', fontSize=9, fontName='Helvetica-Bold', textColor=BLUE_DARK,
        spaceBefore=4, spaceAfter=2)))
    far_calc = [["Use", "FAR", "Max ZFA"]]
    if env.residential_far and lot_area:
        far_calc.append(["Res.", f"{env.residential_far:.2f}",
                         f"{env.residential_far * lot_area:,.0f} SF"])
    if env.commercial_far and lot_area:
        far_calc.append(["Comm.", f"{env.commercial_far:.2f}",
                         f"{env.commercial_far * lot_area:,.0f} SF"])
    if env.cf_far and lot_area:
        far_calc.append(["CF", f"{env.cf_far:.2f}",
                         f"{env.cf_far * lot_area:,.0f} SF"])
    if env.ih_bonus_far and lot_area:
        far_calc.append(["IH Bonus", f"+{env.ih_bonus_far:.2f}",
                         f"+{env.ih_bonus_far * lot_area:,.0f} SF"])
    if len(far_calc) > 1:
        far_w = [0.65 * inch, 0.55 * inch, calc_half - 1.2 * inch]
        left_parts.append(_make_data_table(far_calc, col_widths=far_w))

    # ══════════════════════════════════════════════════════════════
    # RIGHT COLUMN: Unit Count + Height
    # ══════════════════════════════════════════════════════════════
    right_parts = []

    # 6c. Unit Count
    right_parts.append(Paragraph("<b>6c. Residential Unit Count</b>", ParagraphStyle(
        'C6c', fontSize=9, fontName='Helvetica-Bold', textColor=BLUE_DARK, spaceAfter=2)))
    if env.residential_far and lot_area:
        max_res_zfa = env.residential_far * lot_area
        du_factor = 680
        raw_units = max_res_zfa / du_factor
        rounded_units = int(raw_units) + 1 if raw_units - int(raw_units) >= 0.75 else int(raw_units)
        unit_calc = [
            ["Max Res. ZFA", f"{max_res_zfa:,.0f} SF"],
            ["DU Factor", f"{du_factor} SF/unit"],
            ["Raw Count", f"{raw_units:.2f}"],
            ["Rounding", "\u2265 0.75 rounds up"],
            ["Max DUs", str(rounded_units)],
        ]
        right_parts.append(_make_kv_table(unit_calc, col_widths=calc_kv))
    else:
        right_parts.append(Paragraph("Residential not permitted.", styles['SmallBody']))

    # 6d. Height
    right_parts.append(Paragraph("<b>6d. Height &amp; Floor Count</b>", ParagraphStyle(
        'C6d', fontSize=9, fontName='Helvetica-Bold', textColor=BLUE_DARK,
        spaceBefore=4, spaceAfter=2)))
    height_calc = []
    if env.quality_housing:
        height_calc.append(["Program", "Quality Housing"])
        ground_fl = 15
        typical_fl = 10
        if env.base_height_min is not None and env.base_height_max is not None:
            height_calc.append(["Base Ht Range",
                                f"{env.base_height_min}\u2013{env.base_height_max}'"])
            base_floors = 1 + max(0, int((env.base_height_max - ground_fl) / typical_fl))
            height_calc.append(["Base Floors", f"{base_floors}"])
        if env.max_building_height is not None:
            height_calc.append(["Max Height", f"{env.max_building_height}'"])
            if env.base_height_max:
                sb_fl = max(0, int((env.max_building_height - env.base_height_max) / typical_fl))
                height_calc.append(["Setback Floors", f"{sb_fl}"])
                height_calc.append(["Total Floors", str(base_floors + sb_fl)])
    elif env.height_factor:
        height_calc.append(["Program", "Height Factor"])
        height_calc.append(["Max Height", "No cap (SEP)"])
        if env.sky_exposure_plane:
            sep = env.sky_exposure_plane
            height_calc.append(["SEP Start", f"{sep.start_height}'"])
            height_calc.append(["SEP Ratio", f"{sep.ratio}:1"])
    else:
        if env.max_building_height is not None:
            height_calc.append(["Max Height", f"{env.max_building_height}'"])
    if height_calc:
        right_parts.append(_make_kv_table(height_calc, col_widths=calc_kv))

    # ── Assemble two-column layout ──
    left_inner = Table([[p] for p in left_parts], colWidths=[calc_half])
    left_inner.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    right_inner = Table([[p] for p in right_parts], colWidths=[calc_half])
    right_inner.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    two_col = Table([[left_inner, right_inner]], colWidths=[calc_half + 4, calc_half + 4])
    two_col.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(two_col)
    story.append(Spacer(1, 8))


# ──────────────────────────────────────────────────────────────────
# SECTION 7: DEVELOPMENT SCENARIOS  (with 3D massing images)
# ──────────────────────────────────────────────────────────────────

def _build_highlight_badges(scenario, lot=None, envelope=None):
    """Build a row of small pill badges for scenario characteristics."""
    badges = []

    # Primary badge: scenario name
    badges.append(("primary", scenario.name))

    # Conditional badges
    if lot and getattr(lot, 'street_width', None) == "wide":
        badges.append(("technical", "Wide Street"))
    if scenario.parking and scenario.parking.waiver_eligible:
        badges.append(("positive", "Parking Waived"))
    if envelope and getattr(envelope, 'quality_housing', False):
        badges.append(("technical", "Quality Housing"))
    if "UAP" in scenario.name:
        badges.append(("positive", "UAP Bonus"))
    if "4+1" in scenario.name or "Penthouse" in scenario.name:
        badges.append(("technical", "Penthouse Rule"))
    if "MIH" in scenario.name or "Inclusionary" in scenario.name:
        badges.append(("positive", "MIH Required"))
    if "Tower" in scenario.name:
        badges.append(("technical", "Tower-on-Base"))

    if not badges:
        return None

    # Build pill cells
    badge_style = ParagraphStyle(
        '_badge', fontName='Helvetica-Bold', fontSize=6.5,
        leading=8, alignment=TA_CENTER,
    )
    cells = []
    bg_map = {
        "primary": (GOLD_LIGHT, DARK),
        "positive": (BADGE_GREEN, colors.HexColor('#1B5E20')),
        "technical": (BADGE_BLUE, BLUE_DARK),
    }
    for btype, label in badges:
        bg, fg = bg_map.get(btype, (GOLD_LIGHT, DARK))
        p = Paragraph(f'<font color="{fg.hexval()}">{label}</font>', badge_style)
        cells.append(p)

    # Create a single-row table with one cell per badge
    col_w = CONTENT_W / max(len(cells), 1)
    t = Table([cells], colWidths=[col_w] * len(cells))
    style_cmds = [
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    for idx, (btype, _) in enumerate(badges):
        bg, _ = bg_map.get(btype, (GOLD_LIGHT, DARK))
        style_cmds.append(('BACKGROUND', (idx, 0), (idx, 0), bg))
    t.setStyle(TableStyle(style_cmds))
    return t


def _build_scenario_manifest_table(scenario, styles):
    """Build the development summary table for a single scenario."""
    s = scenario
    gross_sf = s.total_gross_sf
    net_sf = s.total_net_sf
    zfa = s.zoning_floor_area or gross_sf
    loss_pct = f"{s.loss_factor.loss_factor_pct:.1f}%" if s.loss_factor else "\u2014"
    eff_ratio = f"{s.loss_factor.efficiency_ratio*100:.1f}%" if s.loss_factor else "\u2014"
    avg_unit_sf = f"{s.unit_mix.average_unit_sf:,.0f}" if s.unit_mix else "\u2014"
    parking_spaces = str(s.parking.total_spaces_required) if s.parking else "\u2014"
    waiver = "Yes" if (s.parking and s.parking.waiver_eligible) else "No"

    rows = [
        ["", ""],
        ["Total Units", str(s.total_units) if s.total_units else "\u2014"],
        ["Zoning Floor Area (ZFA)", f"{zfa:,.0f} SF"],
        ["Gross Building Area", f"{gross_sf:,.0f} SF"],
        ["Net Rentable Area", f"{net_sf:,.0f} SF"],
        ["Loss Factor", loss_pct],
        ["Efficiency Ratio", eff_ratio],
        ["Avg Unit Rentable SF", avg_unit_sf],
        ["Residential SF", f"{s.residential_sf:,.0f} SF" if s.residential_sf else "\u2014"],
        ["Commercial SF", f"{s.commercial_sf:,.0f} SF" if s.commercial_sf else "\u2014"],
        ["Community Facility SF", f"{s.cf_sf:,.0f} SF" if s.cf_sf else "\u2014"],
        ["Parking Spaces", parking_spaces],
        ["Waiver Eligible", waiver],
        ["FAR Used", f"{s.far_used:.2f}"],
        ["Max Height", f"{s.max_height_ft:.0f} ft"],
        ["Floors", str(s.num_floors)],
    ]

    col_widths = [2.8 * inch, CONTENT_W - 2.8 * inch]
    t = Table(rows, colWidths=col_widths)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7.5),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('TEXTCOLOR', (0, 1), (0, -1), DARK),
        ('TEXTCOLOR', (1, 1), (1, -1), colors.HexColor('#444444')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, BLUE),
        ('LINEBELOW', (0, 1), (-1, -2), 0.25, GRID_COLOR),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, GRID_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), LIGHT_BG))
    t.setStyle(TableStyle(style_cmds))
    return t


def _build_development_scenarios(story, styles, scenarios, lot=None, envelope=None, massing_models=None):
    """Section 7: Investment case study format — scenario name, executive takeaway,
    key metrics row, detailed program, optional 3D massing, and development summary."""
    story.append(PageBreak())
    story.append(_section_header("Development Scenarios", section_num=7, styles=styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Each scenario below represents a distinct development strategy evaluated "
        "against the applicable zoning controls for this site.",
        styles['Body'],
    ))
    story.append(Spacer(1, 6))

    # Lazy-import the renderer so we don't crash if matplotlib is missing
    render_fn = None
    try:
        from app.services.render_3d import render_massing_views
        render_fn = render_massing_views
    except Exception:
        pass

    col_half = CONTENT_W / 2 - 4  # Half width for two-column layout
    kv_half = [1.2 * inch, col_half - 1.2 * inch]  # KV table widths within half

    for i, scenario in enumerate(scenarios):
        # ── Investment case study header ──
        sc_title = Paragraph(
            f"<b>Scenario {i+1}: {scenario.name}</b>",
            ParagraphStyle('ScCaseTitle', fontSize=13, fontName='Helvetica-Bold',
                           textColor=DARK, leading=16),
        )
        sc_bar = Table([[sc_title]], colWidths=[CONTENT_W])
        sc_bar.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('LINEBEFORE', (0, 0), (0, -1), 3, GOLD),
            ('LINEABOVE', (0, 0), (-1, 0), 0.75, GRID_COLOR),
        ]))
        story.append(sc_bar)

        # ── Highlight badges ──
        badges = _build_highlight_badges(scenario, lot, envelope)
        if badges:
            story.append(badges)

        # ── Executive takeaway (2-3 sentence summary) ──
        story.append(Spacer(1, 3))
        story.append(Paragraph(scenario.description, styles['ExecutiveSummary']))
        story.append(Spacer(1, 3))

        # ── Key Metrics summary row (Units | ZFA | FAR | Height | Efficiency) ──
        km_cells_top = []
        km_cells_bot = []
        km_style_lbl = ParagraphStyle('_kmLbl', fontSize=7, fontName='Helvetica',
                                       textColor=GREY, alignment=TA_CENTER, leading=9)
        km_style_val = ParagraphStyle('_kmVal', fontSize=16, fontName='Helvetica-Bold',
                                       textColor=BLUE, alignment=TA_CENTER, leading=19)
        km_metrics = []
        if scenario.total_units > 0:
            km_metrics.append(("Units", str(scenario.total_units)))
        if scenario.zoning_floor_area:
            km_metrics.append(("ZFA", f"{scenario.zoning_floor_area:,.0f}"))
        km_metrics.append(("FAR", f"{scenario.far_used:.2f}"))
        km_metrics.append(("Height", f"{scenario.max_height_ft:.0f}'"))
        km_metrics.append(("Floors", str(scenario.num_floors)))
        if scenario.loss_factor:
            km_metrics.append(("Efficiency", f"{scenario.loss_factor.efficiency_ratio*100:.0f}%"))

        for lbl, val in km_metrics:
            km_cells_top.append(Paragraph(val, km_style_val))
            km_cells_bot.append(Paragraph(lbl, km_style_lbl))

        nkm = len(km_metrics)
        km_w = CONTENT_W / nkm
        km_t = Table([km_cells_top, km_cells_bot], colWidths=[km_w] * nkm)
        km_t.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
            ('TOPPADDING', (0, 1), (-1, 1), 0),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, GRID_COLOR),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, GRID_COLOR),
            *[('LINEBEFORE', (j, 0), (j, -1), 0.25, GRID_COLOR) for j in range(1, nkm)],
        ]))
        story.append(km_t)
        story.append(Spacer(1, 6))

        # ── BUILD LEFT COLUMN: summary + core + efficiency + parking ──
        left_parts = []

        # Summary metrics
        lh_sum = Paragraph("<b>Summary</b>", ParagraphStyle(
            'ColH2', fontSize=9, fontName='Helvetica-Bold', textColor=BLUE_DARK, spaceAfter=2))
        left_parts.append(lh_sum)

        sc_data = [
            ["ZFA", f"{scenario.zoning_floor_area:,.0f} SF"
             if scenario.zoning_floor_area else "N/A"],
            ["Gross SF", f"{scenario.total_gross_sf:,.0f}"],
            ["Net SF", f"{scenario.total_net_sf:,.0f}"],
            ["Floors", str(scenario.num_floors)],
            ["Height", f"{scenario.max_height_ft:.0f} ft"],
            ["FAR Used", f"{scenario.far_used:.2f}"],
        ]
        if scenario.residential_sf > 0:
            sc_data.append(["Res. SF", f"{scenario.residential_sf:,.0f}"])
        if scenario.commercial_sf > 0:
            sc_data.append(["Comm. SF", f"{scenario.commercial_sf:,.0f}"])
        if scenario.cf_sf > 0:
            sc_data.append(["CF SF", f"{scenario.cf_sf:,.0f}"])
        if scenario.total_units > 0:
            sc_data.append(["Units", str(scenario.total_units)])
        left_parts.append(_make_kv_table(sc_data, col_widths=kv_half))

        # Building core
        if scenario.core:
            core = scenario.core
            lh_core = Paragraph("<b>Building Core</b>", ParagraphStyle(
                'ColH2c', fontSize=9, fontName='Helvetica-Bold', textColor=BLUE_DARK,
                spaceBefore=4, spaceAfter=2))
            left_parts.append(lh_core)
            core_data = [
                ["Stairs", f"{core.stairs} ({core.stair_sf_per_floor:.0f} SF/fl)"],
                ["Elevators", f"{core.elevators} ({core.elevator_sf_per_floor:.0f} SF/fl)"],
                ["MEP", f"{core.mechanical_sf_per_floor:.0f} SF/fl"],
                ["Corridor", f"{core.corridor_sf_per_floor:.0f} SF/fl"],
                ["Core Total",
                 f"{core.total_core_sf_per_floor:.0f} SF ({core.core_percentage:.1f}%)"],
            ]
            left_parts.append(_make_kv_table(core_data, col_widths=kv_half))

        # Efficiency / loss factor
        if scenario.loss_factor:
            lf = scenario.loss_factor
            left_parts.append(Paragraph(
                f"<b>Efficiency:</b> {lf.efficiency_ratio*100:.1f}% "
                f"(loss: {lf.loss_factor_pct:.1f}%)",
                styles['SmallBody'],
            ))

        # Parking
        if scenario.parking and scenario.parking.total_spaces_required > 0:
            pk_parts_list = [f"<b>Parking:</b> {scenario.parking.total_spaces_required} sp."]
            if scenario.parking.waiver_eligible:
                pk_parts_list.append(" (waiver eligible)")
            left_parts.append(Paragraph("".join(pk_parts_list), styles['SmallBody']))

        # ── BUILD RIGHT COLUMN: unit mix + floor-by-floor ──
        right_parts = []

        # Unit mix
        if scenario.unit_mix and scenario.unit_mix.total_units > 0:
            rh_um = Paragraph("<b>Unit Mix</b>", ParagraphStyle(
                'ColH2u', fontSize=9, fontName='Helvetica-Bold', textColor=BLUE_DARK, spaceAfter=2))
            right_parts.append(rh_um)
            um_data = [["Type", "Count", "Avg SF"]]
            for u in scenario.unit_mix.units:
                um_data.append([
                    u.type.replace("br", " BR").replace("studio", "Studio").capitalize(),
                    str(u.count),
                    f"{u.avg_sf}",
                ])
            um_data.append(["Total", str(scenario.unit_mix.total_units),
                            f"{scenario.unit_mix.average_unit_sf:.0f}"])
            um_w = [1.1 * inch, 0.6 * inch, col_half - 1.7 * inch]
            um_t = _make_data_table(um_data, col_widths=um_w)
            right_parts.append(um_t)

        # Floor-by-floor
        if scenario.floors and len(scenario.floors) <= 40:
            rh_fl = Paragraph("<b>Floor Breakdown</b>", ParagraphStyle(
                'ColH2f', fontSize=9, fontName='Helvetica-Bold', textColor=BLUE_DARK,
                spaceBefore=4, spaceAfter=2))
            right_parts.append(rh_fl)
            fl_data = [["Fl", "Use", "Gross", "Ht"]]
            for fl in scenario.floors:
                fl_data.append([
                    str(fl.floor),
                    fl.use.replace("_", " ").title()[:8],
                    f"{fl.gross_sf:,.0f}",
                    f"{fl.height_ft:.0f}'",
                ])
            fl_w = [0.35 * inch, 0.8 * inch, 0.65 * inch, col_half - 1.8 * inch - 0.05 * inch]
            fl_t = _make_data_table(fl_data, col_widths=fl_w)
            right_parts.append(fl_t)

        # ── Assemble two-column layout ──
        # Stack each column's parts into a single cell using a nested table
        left_cell = left_parts if left_parts else [""]
        right_cell = right_parts if right_parts else [""]

        # Inner tables for each column (stack flowables vertically)
        left_inner = Table([[p] for p in left_cell], colWidths=[col_half])
        left_inner.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        right_inner = Table([[p] for p in right_cell], colWidths=[col_half])
        right_inner.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        two_col = Table([[left_inner, right_inner]], colWidths=[col_half + 4, col_half + 4])
        two_col.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(two_col)

        # ── 3D MASSING IMAGES (side-by-side: perspective + plan) ──
        if render_fn and massing_models and scenario.name in massing_models:
            try:
                views = render_fn(massing_models[scenario.name], scenario.name)
                has_persp = bool(views.get("perspective"))
                has_plan = bool(views.get("plan"))

                if has_persp and has_plan:
                    # Side-by-side layout: perspective (left) + plan (right)
                    story.append(Spacer(1, 4))
                    story.append(Paragraph("3D Massing Views",
                                           styles['SubSection']))
                    persp_img = _image_from_bytes(views["perspective"], 3.6 * inch, 2.5 * inch)
                    plan_img = _image_from_bytes(views["plan"], 2.8 * inch, 2.8 * inch)
                    side_t = Table(
                        [[persp_img, plan_img]],
                        colWidths=[3.8 * inch, 3.0 * inch],
                    )
                    side_t.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('TOPPADDING', (0, 0), (-1, -1), 2),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ]))
                    story.append(side_t)
                elif has_persp:
                    story.append(Spacer(1, 4))
                    story.append(Paragraph("3D Massing \u2014 Perspective View",
                                           styles['SubSection']))
                    img = _image_from_bytes(views["perspective"], 5.0 * inch, 3.5 * inch)
                    img_t = Table([[img]], colWidths=[CONTENT_W])
                    img_t.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ]))
                    story.append(img_t)
                elif has_plan:
                    story.append(Spacer(1, 4))
                    story.append(Paragraph("3D Massing \u2014 Plan View",
                                           styles['SubSection']))
                    img2 = _image_from_bytes(views["plan"], 3.0 * inch, 3.0 * inch)
                    img_t2 = Table([[img2]], colWidths=[CONTENT_W])
                    img_t2.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ]))
                    story.append(img_t2)

                story.append(Paragraph(
                    "Rendered from massing model. Colours indicate use type. "
                    "Not to architectural scale.",
                    styles['NoteText'],
                ))
            except Exception as e:
                logger.warning("Failed to render 3D massing for '%s': %s",
                               scenario.name, e)

        # ── Development Summary ──
        story.append(Spacer(1, 4))
        story.append(Paragraph("Development Summary", styles['SubSection']))
        manifest_t = _build_scenario_manifest_table(scenario, styles)
        story.append(manifest_t)

        # ── Scenario separator ──
        story.append(Spacer(1, 12))
        story.append(HRFlowable(width="50%", thickness=0.25, color=GRID_COLOR, hAlign='CENTER'))
        story.append(Spacer(1, 12))


# ──────────────────────────────────────────────────────────────────
# SECTION 8: SCENARIO COMPARISON
# ──────────────────────────────────────────────────────────────────

def _build_comparison_table(story, styles, scenarios):
    """Section 8: Side-by-side scenario comparison table."""
    if not scenarios:
        return

    story.append(PageBreak())
    story.append(_section_header("Scenario Comparison", section_num=8, styles=styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Side-by-side comparison of all evaluated development programs for this site:",
        styles['Body'],
    ))
    story.append(Spacer(1, 4))

    # Build wrapping Paragraph headers so long names don't overflow
    from reportlab.lib.styles import ParagraphStyle as _PS
    _hdr_style = _PS(
        "_cmp_hdr", fontName="Helvetica-Bold",
        fontSize=6.5, leading=7.5, alignment=1,  # center
        textColor=WHITE,
    )
    _short_names = {
        "Max Residential": "Max Res.",
        "Max Units": "Max Units",
        "4+1 Penthouse (No Elevator)": "4+1 PH\n(No Elev.)",
        "Community Facility": "CF",
        "Residential + Community Facility": "Res. + CF",
        "Height Factor Option": "Height\nFactor",
        "UAP (City of Yes)": "UAP\n(CoY)",
    }
    headers = [Paragraph("<b>Metric</b>", _hdr_style)] + [
        Paragraph(
            f"<b>{_short_names.get(s.name, s.name[:18])}</b>",
            _hdr_style,
        )
        for s in scenarios
    ]

    rows = [headers]

    def _row(label, getter):
        return [label] + [getter(s) for s in scenarios]

    rows.append(_row("Total ZFA",
                      lambda s: f"{s.zoning_floor_area:,.0f}" if s.zoning_floor_area else "N/A"))
    rows.append(_row("Total Gross SF", lambda s: f"{s.total_gross_sf:,.0f}"))
    rows.append(_row("Max Height (ft)", lambda s: f"{s.max_height_ft:.0f}"))
    rows.append(_row("Floors", lambda s: str(s.num_floors)))
    rows.append(_row("FAR Used", lambda s: f"{s.far_used:.2f}"))
    rows.append(_row("Residential SF",
                      lambda s: f"{s.residential_sf:,.0f}" if s.residential_sf else "\u2014"))
    rows.append(_row("Commercial SF",
                      lambda s: f"{s.commercial_sf:,.0f}" if s.commercial_sf else "\u2014"))
    rows.append(_row("Total Units",
                      lambda s: str(s.total_units) if s.total_units else "\u2014"))
    rows.append(_row("Parking Spaces",
                      lambda s: str(s.parking.total_spaces_required) if s.parking else "\u2014"))
    rows.append(_row("Loss Factor",
                      lambda s: f"{s.loss_factor.loss_factor_pct:.1f}%"
                      if s.loss_factor else "\u2014"))

    ncols = len(headers)
    metric_col = 1.1 * inch
    remaining = CONTENT_W - metric_col
    data_col = remaining / max(ncols - 1, 1)
    col_widths = [metric_col] + [data_col] * (ncols - 1)
    font_size = 7 if ncols > 5 else 8

    t = Table(rows, colWidths=col_widths)
    style_cmds = [
        ('FONTSIZE', (0, 1), (-1, -1), font_size),   # data rows
        ('FONTSIZE', (0, 0), (-1, 0), 1),             # header row (Paragraph handles font)
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), BLUE),
        ('TEXTCOLOR', (0, 1), (0, -1), DARK),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, BLUE),
        ('LINEBELOW', (0, 1), (-1, -2), 0.25, GRID_COLOR),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, GRID_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
    ]
    # Alternating row shading
    for row_i in range(1, len(rows)):
        if row_i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, row_i), (-1, row_i), LIGHT_BG))
    # Highlight best scenario (highest gross SF)
    if scenarios:
        best_idx = max(range(len(scenarios)), key=lambda i: scenarios[i].total_gross_sf)
        style_cmds.append(('BACKGROUND', (best_idx + 1, 1), (best_idx + 1, -1), GREEN_BG))
    t.setStyle(TableStyle(style_cmds))
    story.append(t)
    story.append(Spacer(1, 4))

    if scenarios:
        best = max(scenarios, key=lambda s: s.total_gross_sf)
        story.append(Paragraph(
            f"<i>Highlighted column: highest buildable SF scenario ({best.name})</i>",
            styles['NoteText'],
        ))


# ──────────────────────────────────────────────────────────────────
# SECTION 9: PARKING ANALYSIS  (no dollar amounts)
# ──────────────────────────────────────────────────────────────────

def _build_parking_analysis(story, styles, scenarios, parking_layout_result=None):
    """Section 9: Parking analysis with configuration options (no dollar amounts)."""
    story.append(Spacer(1, 8))
    story.append(_section_header("Parking Analysis", section_num=9, styles=styles))
    story.append(Spacer(1, 4))

    has_parking = any(s.parking and s.parking.total_spaces_required > 0 for s in scenarios)
    if not has_parking:
        story.append(Paragraph(
            "No parking is required for any evaluated scenario. "
            "This may be due to transit zone location or small building waiver eligibility.",
            styles['Body'],
        ))
        return

    pk_data = [["Scenario", "Res Spaces", "Comm Spaces", "Total", "Waiver"]]
    for s in scenarios:
        if s.parking:
            pk_data.append([
                s.name[:30],
                str(s.parking.residential_spaces_required),
                str(s.parking.commercial_spaces_required),
                str(s.parking.total_spaces_required),
                "Yes" if s.parking.waiver_eligible else "No",
            ])
    story.append(_make_data_table(pk_data, col_widths=[
        2.4 * inch, 0.85 * inch, 0.85 * inch, 0.75 * inch, 0.7 * inch,
    ]))
    story.append(Spacer(1, 6))

    if parking_layout_result:
        _build_parking_layout_section(story, styles, parking_layout_result)


def _build_parking_layout_section(story, styles, layout_result):
    """Parking layout options — no dollar amounts."""
    story.append(Paragraph("Parking Configuration Options", styles['SubSection']))
    story.append(Paragraph(
        f"Required spaces: {layout_result.required_spaces}. "
        f"All feasible configurations evaluated:",
        styles['SmallBody'],
    ))
    story.append(Spacer(1, 4))

    for opt in layout_result.options:
        if not opt.feasible:
            continue
        story.append(Paragraph(
            f"<b>{_config_type_label(opt.config_type)}</b>",
            styles['Body'],
        ))
        opt_data = [
            ["Spaces Provided", str(opt.spaces_provided)],
            ["Meets Requirement", "Yes" if opt.meets_requirement else "No"],
            ["Area Consumed", f"{opt.area_consumed_sf:,.0f} SF"],
            ["Impact on Buildable", f"{opt.impact_on_buildable:,.0f} SF"],
            ["Floors Consumed",
             ", ".join(opt.floors_consumed) if opt.floors_consumed else "N/A"],
        ]
        story.append(_make_kv_table(opt_data, col_widths=[2 * inch, 4.5 * inch]))

        if opt.feasibility_notes:
            for note in opt.feasibility_notes:
                story.append(Paragraph(f"\u2022 {note}", styles['NoteText']))
        story.append(Spacer(1, 4))

    if layout_result.recommended:
        rec = layout_result.recommended
        story.append(Paragraph(
            f"<b>Recommended:</b> {_config_type_label(rec.config_type)} \u2014 "
            f"{rec.spaces_provided} spaces, "
            f"{rec.impact_on_buildable:,.0f} SF impact on buildable area.",
            styles['Body'],
        ))

    if layout_result.waiver_note:
        story.append(Paragraph(
            f"<i>{layout_result.waiver_note}</i>",
            styles['NoteText'],
        ))


# ──────────────────────────────────────────────────────────────────
# SECTION 10: ASSEMBLAGE ANALYSIS
# ──────────────────────────────────────────────────────────────────

def _build_assemblage_section(story, styles, assemblage_data):
    """Section 10: Assemblage analysis (if applicable)."""
    if not assemblage_data:
        return

    story.append(PageBreak())
    story.append(_section_header("Assemblage Analysis", section_num=10, styles=styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Analysis of combined development potential from merging multiple lots:",
        styles['Body'],
    ))
    story.append(Spacer(1, 4))

    # ── Individual lots ──
    individual_lots = assemblage_data.get("individual_lots", [])
    if individual_lots:
        story.append(Paragraph("10a. Individual Lots", styles['SubSection']))
        for lot_info in individual_lots:
            lot_data = [
                ["BBL", lot_info.get("bbl", "N/A")],
                ["Address", lot_info.get("address", "N/A")],
                ["Lot Area", f"{lot_info.get('lot_area', 0):,.0f} SF"],
                ["Zoning District", lot_info.get("zoning_district", "N/A")],
            ]
            story.append(_make_kv_table(lot_data))
            story.append(Spacer(1, 4))

    # ── Merged lot ──
    merged = assemblage_data.get("merged_lot") or assemblage_data.get("merged")
    if merged:
        story.append(Paragraph("10b. Merged (Assembled) Lot", styles['SubSection']))
        merged_data = [
            ["Combined Lot Area", f"{merged.get('lot_area', 0):,.0f} SF"],
            ["Lot Type", merged.get("lot_type", "N/A")],
        ]
        if merged.get("zoning_district"):
            merged_data.append(["Zoning District", merged["zoning_district"]])
        story.append(_make_kv_table(merged_data))
        story.append(Spacer(1, 4))

        method = assemblage_data.get("contiguity_method", "")
        validated = assemblage_data.get("contiguity_validated", True)
        if method:
            status = "Validated" if validated else "Not validated"
            story.append(Paragraph(
                f"Contiguity: {status} (method: {method})",
                styles['SmallBody'],
            ))
            story.append(Spacer(1, 4))

    # ── Delta summary ──
    delta = assemblage_data.get("delta", {})
    if delta:
        story.append(Paragraph("10c. Assemblage Benefits (Delta)", styles['SubSection']))

        lot_delta_rows = []
        lot_area_change = delta.get("lot_area_change", 0)
        if lot_area_change:
            lot_delta_rows.append(["Lot Area Change",
                f"+{lot_area_change:,.0f} SF" if lot_area_change > 0
                else f"{lot_area_change:,.0f} SF"])
        footprint_gain = delta.get("footprint_gain_sf", 0)
        if footprint_gain:
            lot_delta_rows.append(
                ["Footprint Gain (Side Yard Elimination)", f"+{footprint_gain:,.0f} SF"])
        lot_type_change = delta.get("lot_type_change")
        if lot_type_change:
            lot_delta_rows.append(["Lot Type Change", lot_type_change])
        frontage_change = delta.get("street_frontage_change", {})
        if isinstance(frontage_change, dict) and frontage_change.get("total_change"):
            lot_delta_rows.append(
                ["Frontage Change", f"+{frontage_change['total_change']:.0f} ft"])

        if lot_delta_rows:
            story.append(Paragraph("Lot-Level Changes:", styles['SmallBody']))
            story.append(_make_kv_table(lot_delta_rows))
            story.append(Spacer(1, 4))

        scenario_deltas = delta.get("scenario_deltas", [])
        if scenario_deltas:
            story.append(Paragraph("Per-Scenario Comparison:", styles['SmallBody']))
            header = ["Metric", "Scenario", "Individual", "Assembled", "Change"]
            table_data = [header]
            for sd in scenario_deltas:
                name = sd.get("scenario_name", "N/A")
                far_ind = sd.get("individual_far", 0)
                far_asm = sd.get("assembled_far", 0)
                far_delta = sd.get("far_change", 0)
                table_data.append([
                    "FAR", name,
                    f"{far_ind:.2f}" if far_ind else "N/A",
                    f"{far_asm:.2f}" if far_asm else "N/A",
                    f"{far_delta:+.2f}" if far_delta else "-",
                ])
                zfa_ind = sd.get("individual_zfa", 0)
                zfa_asm = sd.get("assembled_zfa", 0)
                zfa_delta = sd.get("zfa_change", 0)
                table_data.append([
                    "Total ZFA", name,
                    f"{zfa_ind:,.0f} SF" if zfa_ind else "N/A",
                    f"{zfa_asm:,.0f} SF" if zfa_asm else "N/A",
                    f"+{zfa_delta:,.0f} SF" if zfa_delta and zfa_delta > 0
                    else (f"{zfa_delta:,.0f} SF" if zfa_delta else "-"),
                ])
                addl = sd.get("additional_buildable_sf", 0)
                if addl:
                    table_data.append([
                        "Additional Buildable", name, "-", "-", f"+{addl:,.0f} SF",
                    ])
                ht_delta = sd.get("height_change", 0)
                if ht_delta:
                    table_data.append([
                        "Height Change", name, "", "", f"{ht_delta:+.0f} ft",
                    ])
                unit_delta = sd.get("unit_change", 0)
                if unit_delta:
                    table_data.append([
                        "Unit Change", name, "", "", f"{unit_delta:+d} units",
                    ])

            story.append(_make_data_table(table_data, col_widths=[
                1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch,
            ]))
            story.append(Spacer(1, 4))

    # ── Key Unlocks ──
    key_unlocks = delta.get("key_unlocks", []) if delta else []
    if not key_unlocks:
        key_unlocks = assemblage_data.get("key_unlocks", [])
    if key_unlocks:
        story.append(Paragraph("10d. Key Zoning Unlocks", styles['SubSection']))
        story.append(Paragraph(
            "Assembling these lots unlocks the following zoning advantages:",
            styles['SmallBody'],
        ))
        for unlock in key_unlocks:
            story.append(Paragraph(f"\u2713  {unlock}", styles['SmallBody']))
        story.append(Spacer(1, 4))

    # ── Warnings ──
    warnings_list = assemblage_data.get("warnings", [])
    if warnings_list:
        story.append(Paragraph("Assemblage Warnings:", styles['SmallBody']))
        for w in warnings_list:
            story.append(Paragraph(f"\u2022  {w}", styles['SmallBody']))


# ──────────────────────────────────────────────────────────────────
# SECTION 11: NOTES & DISCLAIMERS  (no valuation disclaimers)
# ──────────────────────────────────────────────────────────────────

def _build_disclaimers(story, styles, report_id):
    """Section 11: Disclaimers & Limitations (no dollar / valuation references)."""
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
    story.append(Spacer(1, 6))
    story.append(_section_header("Disclaimers & Limitations", section_num=11, styles=styles))
    story.append(Spacer(1, 4))

    disclaimers = [
        "This report is for preliminary feasibility analysis only.",
        "All calculations should be verified by a licensed architect and zoning attorney.",
        "Special permits, variances, and certifications are not included in this analysis.",
        "Environmental review (CEQR/SEQRA) requirements are not addressed.",
        "Landmark and historic district restrictions may apply and are not fully evaluated.",
        "Actual development potential should be confirmed with NYC Department of Buildings "
        "and Department of City Planning.",
        "3D massing renderings are diagrammatic and are not to architectural scale.",
    ]
    for d in disclaimers:
        story.append(Paragraph(f"\u2022 {d}", styles['SmallBody']))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"Data sources: NYC PLUTO, NYC Geoservice/Geoclient, NYC Zoning Resolution, "
        f"City of Yes for Housing Opportunity amendments, ESRI World Imagery. "
        f"Report generated: {datetime.now().strftime('%B %d, %Y %H:%M')}. "
        f"Report ID: {report_id}.",
        styles['Disclaimer'],
    ))


# ──────────────────────────────────────────────────────────────────
# MAIN ENTRY POINTS
# ──────────────────────────────────────────────────────────────────

def generate_report(
    result: CalculationResult,
    parking_layout_result=None,
    assemblage_data: Optional[dict] = None,
    map_images: Optional[dict] = None,
    massing_models: Optional[dict] = None,
) -> str:
    """Generate a comprehensive PDF feasibility report.

    Args:
        result: CalculationResult with lot profile, zoning envelope, and scenarios
        parking_layout_result: Optional ParkingLayoutResult for detailed parking analysis
        assemblage_data: Optional dict with assemblage delta information
        map_images: Optional dict with satellite_bytes / street_bytes / zoning_map_bytes
        massing_models: Optional dict mapping scenario names to massing model dicts

    Returns: file path to the generated PDF
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_id = str(uuid.uuid4())[:8]
    bbl = result.lot_profile.bbl
    filename = f"zoning_feasibility_{bbl}_{report_id}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=1.0 * inch, bottomMargin=0.8 * inch,
        leftMargin=MARGIN, rightMargin=MARGIN,
    )

    styles = _get_styles()
    story = []
    lot = result.lot_profile
    env = result.zoning_envelope

    # 1. Cover page
    _build_cover_page(story, styles, lot, env, report_id, map_images=map_images)

    # 2. Property maps
    _build_property_maps(story, styles, lot, map_images)

    # 3. Site summary (two-column, no dimensions, no $)
    _build_site_summary(story, styles, lot, env)

    # 4. Key development features
    _build_highlighted_features(story, styles, lot, env, scenarios=result.scenarios)

    # 5. Zoning overview (with zoning map)
    _build_zoning_overview(story, styles, lot, env, map_images=map_images)

    # 6. Detailed calculations
    _build_calculation_breakdown(story, styles, lot, env)

    # 7. Development scenarios (with 3D massing, badges, inline manifest)
    _build_development_scenarios(story, styles, result.scenarios,
                                 lot=lot, envelope=env,
                                 massing_models=massing_models)

    # 8. Scenario comparison table
    _build_comparison_table(story, styles, result.scenarios)

    # 9. Parking analysis (no $)
    _build_parking_analysis(story, styles, result.scenarios, parking_layout_result)

    # 10. Assemblage analysis
    _build_assemblage_section(story, styles, assemblage_data)

    # 11. Notes & disclaimers
    _build_disclaimers(story, styles, report_id)

    doc.build(story,
              onFirstPage=_header_footer_first,
              onLaterPages=_header_footer_later)

    with open(filepath, 'wb') as f:
        f.write(buffer.getvalue())

    return filepath


def generate_report_bytes(
    result: CalculationResult,
    parking_layout_result=None,
    assemblage_data: Optional[dict] = None,
    map_images: Optional[dict] = None,
    massing_models: Optional[dict] = None,
) -> bytes:
    """Generate PDF report and return as bytes (for API streaming).

    Same as generate_report but returns raw bytes instead of writing to disk.
    """
    buffer = BytesIO()
    report_id = str(uuid.uuid4())[:8]

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=1.0 * inch, bottomMargin=0.8 * inch,
        leftMargin=MARGIN, rightMargin=MARGIN,
    )

    styles = _get_styles()
    story = []
    lot = result.lot_profile
    env = result.zoning_envelope

    _build_cover_page(story, styles, lot, env, report_id, map_images=map_images)
    _build_property_maps(story, styles, lot, map_images)
    _build_site_summary(story, styles, lot, env)
    _build_highlighted_features(story, styles, lot, env, scenarios=result.scenarios)
    _build_zoning_overview(story, styles, lot, env, map_images=map_images)
    _build_calculation_breakdown(story, styles, lot, env)
    _build_development_scenarios(story, styles, result.scenarios,
                                 lot=lot, envelope=env, massing_models=massing_models)
    _build_comparison_table(story, styles, result.scenarios)
    _build_parking_analysis(story, styles, result.scenarios, parking_layout_result)
    _build_assemblage_section(story, styles, assemblage_data)
    _build_disclaimers(story, styles, report_id)

    doc.build(story,
              onFirstPage=_header_footer_first,
              onLaterPages=_header_footer_later)
    return buffer.getvalue()


# ──────────────────────────────────────────────────────────────────
# UTILITY HELPERS
# ──────────────────────────────────────────────────────────────────

def _borough_name(code: int) -> str:
    return {
        1: "Manhattan", 2: "Bronx", 3: "Brooklyn",
        4: "Queens", 5: "Staten Island",
    }.get(code, "Unknown")


def _format_bbl(bbl: str) -> str:
    """Format BBL with dashes: borough-block-lot (e.g., '3-04622-0022')."""
    if not bbl or len(bbl) != 10:
        return bbl or "N/A"
    return f"{bbl[0]}-{bbl[1:6]}-{bbl[6:10]}"


def _config_type_label(config_type: str) -> str:
    """Human-readable label for parking configuration type."""
    labels = {
        "surface_lot": "At-Grade Surface Parking",
        "below_grade_1_level": "Below-Grade (1 Level)",
        "below_grade_2_levels": "Below-Grade (2 Levels)",
        "enclosed_at_grade": "Enclosed At-Grade (Ground Floor)",
        "mechanical_stackers_double": "Mechanical Stackers (Double)",
        "mechanical_stackers_triple": "Mechanical Stackers (Triple)",
        "ramp_to_2nd_floor": "Ramp to 2nd Floor Parking",
    }
    return labels.get(config_type, config_type.replace("_", " ").title())


def _land_use_desc(code: str) -> str:
    """Human-readable land use description from PLUTO code."""
    codes = {
        "01": "One & Two Family Buildings",
        "02": "Multi-Family Walk-Up Buildings",
        "03": "Multi-Family Elevator Buildings",
        "04": "Mixed Residential & Commercial",
        "05": "Commercial & Office Buildings",
        "06": "Industrial & Manufacturing",
        "07": "Transportation & Utility",
        "08": "Public Facilities & Institutions",
        "09": "Open Space & Recreation",
        "10": "Parking Facilities",
        "11": "Vacant Land",
    }
    # Try zero-padded first, then raw code
    return codes.get(code, codes.get(code.zfill(2), f"Code {code}"))


def _zoning_district_desc(district: str) -> str:
    """Brief description of a zoning district."""
    if not district:
        return ""
    prefix = district[:2].upper()
    descs = {
        "R1": "Low-density residential (detached single-family)",
        "R2": "Low-density residential (single/two-family)",
        "R3": "Low-density residential (one/two-family, some townhouses)",
        "R4": "Low-density residential (one/two-family, townhouses)",
        "R5": "Low-density residential (small apartment buildings)",
        "R6": "Medium-density residential (apartment buildings)",
        "R7": "Medium-density residential (apartment buildings, elevator)",
        "R8": "High-density residential (large apartment buildings)",
        "R9": "High-density residential (towers, large developments)",
        "R10": "Highest-density residential (Manhattan core)",
        "C1": "Local retail commercial overlay",
        "C2": "Local service commercial overlay",
        "C3": "Waterfront/amusement commercial",
        "C4": "General commercial (major retail)",
        "C5": "Central commercial (office/retail)",
        "C6": "General central commercial (high-density)",
        "C7": "Amusement district",
        "C8": "Auto-related commercial",
        "M1": "Light manufacturing/commercial",
        "M2": "Medium manufacturing",
        "M3": "Heavy manufacturing",
    }
    return descs.get(prefix, "")
