"""
PDF report generator for zoning feasibility analysis.
Uses ReportLab to generate professional reports with West Egg Development branding.

Sections:
  1.  Cover Page (with West Egg Development branding + satellite thumbnail)
  2.  Property Maps (satellite + street)
  3.  Site Summary (two-column layout)
  4.  Key Development Features (highlighted callout cards)
  5.  Zoning Overview (with zoning map)
  6.  Detailed Calculations (FAR, units, height breakdowns)
  7.  Development Scenarios (with 3D massing renderings)
  8.  Scenario Comparison Table
  9.  Parking Analysis
  10. Assemblage Analysis (if applicable)
  11. Notes & Disclaimers
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

# ── Brand Colors ──
BLUE = colors.HexColor('#4A90D9')
BLUE_DARK = colors.HexColor('#2C5F8A')
DARK = colors.HexColor('#1a1a2e')
GREY = colors.HexColor('#666666')
LIGHT_BG = colors.HexColor('#f0f4f8')
GRID_COLOR = colors.HexColor('#e0e0e0')
GREEN_BG = colors.HexColor('#e8f4e8')
HIGHLIGHT_BORDER = colors.HexColor('#4A90D9')
FEATURE_BG = colors.HexColor('#f7f9fc')
GOLD = colors.HexColor('#D4A017')
GOLD_LIGHT = colors.HexColor('#FFF8E1')
WHITE = colors.white

PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch
CONTENT_W = PAGE_W - 2 * MARGIN  # ~504 pt ≈ 7 inches


# ──────────────────────────────────────────────────────────────────
# LOGO & HEADER / FOOTER (drawn on canvas)
# ──────────────────────────────────────────────────────────────────

def _draw_logo(canvas, x, y, size="small"):
    """Draw the West Egg Development logo on the canvas.

    *x, y* is the left-centre of the gold circle.
    """
    canvas.saveState()
    if size == "large":
        r, fs, ls, gap = 18, 14, 16, 24
    else:
        r, fs, ls, gap = 10, 8, 9, 14

    # Gold circle
    canvas.setFillColor(GOLD)
    canvas.circle(x + r, y, r, fill=1, stroke=0)

    # "WE" inside circle
    canvas.setFillColor(WHITE)
    canvas.setFont('Helvetica-Bold', fs)
    canvas.drawCentredString(x + r, y - fs * 0.35, "WE")

    # Company name
    canvas.setFillColor(DARK)
    canvas.setFont('Helvetica-Bold', ls)
    canvas.drawString(x + r * 2 + gap * 0.4, y - ls * 0.35, "WEST EGG DEVELOPMENT")
    canvas.restoreState()


def _header_footer_first(canvas, doc):
    """Cover page — logo + gold rule; no page number."""
    canvas.saveState()
    _draw_logo(canvas, doc.leftMargin, PAGE_H - 38, size="small")
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.5)
    canvas.line(doc.leftMargin, PAGE_H - 52, PAGE_W - doc.rightMargin, PAGE_H - 52)
    canvas.restoreState()


def _header_footer_later(canvas, doc):
    """Subsequent pages — logo left, report title right, page number footer."""
    canvas.saveState()

    # ── Header ──
    _draw_logo(canvas, doc.leftMargin, PAGE_H - 38, size="small")
    canvas.setFillColor(GREY)
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(PAGE_W - doc.rightMargin, PAGE_H - 41,
                           "Zoning Feasibility Analysis")
    canvas.setStrokeColor(BLUE_DARK)
    canvas.setLineWidth(1)
    canvas.line(doc.leftMargin, PAGE_H - 52, PAGE_W - doc.rightMargin, PAGE_H - 52)

    # ── Footer ──
    canvas.setStrokeColor(GRID_COLOR)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 42, PAGE_W - doc.rightMargin, 42)
    canvas.setFillColor(GREY)
    canvas.setFont('Helvetica', 8)
    canvas.drawCentredString(PAGE_W / 2, 28, f"Page {doc.page}")
    canvas.drawRightString(PAGE_W - doc.rightMargin, 28,
                           datetime.now().strftime('%B %d, %Y'))
    canvas.restoreState()


# ──────────────────────────────────────────────────────────────────
# STYLES
# ──────────────────────────────────────────────────────────────────

def _get_styles():
    """Build all report paragraph styles."""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='ReportTitle', fontSize=26, fontName='Helvetica-Bold',
        spaceAfter=6, textColor=DARK, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='Subtitle', fontSize=12, fontName='Helvetica',
        alignment=TA_CENTER, textColor=GREY,
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle', fontSize=14, fontName='Helvetica-Bold',
        spaceAfter=8, spaceBefore=16, textColor=BLUE,
    ))
    styles.add(ParagraphStyle(
        name='SectionHeaderWhite', fontSize=13, fontName='Helvetica-Bold',
        textColor=WHITE, leading=18,
    ))
    styles.add(ParagraphStyle(
        name='SubSection', fontSize=11, fontName='Helvetica-Bold',
        spaceAfter=4, spaceBefore=8,
    ))
    styles.add(ParagraphStyle(
        name='Body', fontSize=10, fontName='Helvetica',
        spaceAfter=3, leading=13,
    ))
    styles.add(ParagraphStyle(
        name='SmallBody', fontSize=9, fontName='Helvetica',
        spaceAfter=2, leading=11,
    ))
    styles.add(ParagraphStyle(
        name='Disclaimer', fontSize=8, fontName='Helvetica-Oblique',
        textColor=GREY, alignment=TA_CENTER, leading=10,
    ))
    styles.add(ParagraphStyle(
        name='NoteText', fontSize=8, fontName='Helvetica-Oblique',
        textColor=GREY, spaceAfter=2, leading=10,
    ))
    styles.add(ParagraphStyle(
        name='CalloutLabel', fontSize=9, fontName='Helvetica-Bold',
        textColor=DARK, spaceAfter=1, leading=11,
    ))
    styles.add(ParagraphStyle(
        name='CalloutValue', fontSize=9, fontName='Helvetica',
        textColor=GREY, spaceAfter=2, leading=11,
    ))
    styles.add(ParagraphStyle(
        name='BigNumber', fontSize=18, fontName='Helvetica-Bold',
        textColor=BLUE, alignment=TA_CENTER, spaceAfter=4,
    ))
    return styles


# ──────────────────────────────────────────────────────────────────
# TABLE, IMAGE & SECTION HELPERS
# ──────────────────────────────────────────────────────────────────

def _section_header(text, section_num=None, styles=None):
    """Colored section header bar — white text on blue-dark background."""
    label = f"{section_num}. {text}" if section_num else text
    sty = (styles or {}).get('SectionHeaderWhite') or ParagraphStyle(
        'SHW', fontSize=13, fontName='Helvetica-Bold', textColor=WHITE, leading=18,
    )
    p = Paragraph(label, sty)
    t = Table([[p]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BLUE_DARK),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    return t


def _make_kv_table(data: list[list[str]], col_widths=None) -> Table:
    """Compact key-value pair table (label + value)."""
    if col_widths is None:
        col_widths = [2.2 * inch, 4.3 * inch]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), GREY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, GRID_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def _make_data_table(data: list[list[str]], col_widths=None) -> Table:
    """Table with styled header row (white text on blue-dark background)."""
    if col_widths is None:
        ncols = len(data[0]) if data else 1
        w = CONTENT_W / ncols
        col_widths = [w] * ncols
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), BLUE_DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, GRID_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
    ]))
    return t


def _image_from_bytes(image_bytes: bytes, width: float, height: float) -> RLImage:
    """Convert raw PNG/JPEG bytes to a ReportLab Image flowable."""
    buf = BytesIO(image_bytes)
    return RLImage(buf, width=width, height=height)


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
    """Cover page with branding, satellite thumbnail, and lot summary."""
    story.append(Spacer(1, 25))

    # Title
    story.append(Paragraph("Zoning Feasibility Analysis", styles['ReportTitle']))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="55%", thickness=2.5, color=GOLD, hAlign='CENTER'))
    story.append(Spacer(1, 10))

    # Address
    story.append(Paragraph(
        lot.address or "Address Not Available",
        ParagraphStyle('CoverAddr', fontSize=16, alignment=TA_CENTER,
                       textColor=DARK, fontName='Helvetica-Bold'),
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"BBL: {_format_bbl(lot.bbl)}", styles['Subtitle']))
    story.append(Spacer(1, 14))

    # Satellite thumbnail (centred)
    if map_images and map_images.get("satellite_bytes"):
        try:
            img = _image_from_bytes(map_images["satellite_bytes"], 4.0 * inch, 2.5 * inch)
            wrap_t = Table([[img]], colWidths=[CONTENT_W])
            wrap_t.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('TOPPADDING', (0, 0), (0, 0), 0),
                ('BOTTOMPADDING', (0, 0), (0, 0), 0),
            ]))
            story.append(wrap_t)
            story.append(Spacer(1, 10))
        except Exception:
            pass

    # Summary table — NO lot dimensions
    cover_data = [
        ["Borough", _borough_name(lot.borough)],
        ["Lot Area", f"{lot.lot_area:,.0f} SF" if lot.lot_area else "N/A"],
        ["Lot Type", lot.lot_type.capitalize()],
        ["Zoning District", ", ".join(lot.zoning_districts) if lot.zoning_districts else "N/A"],
        ["Date Generated", datetime.now().strftime('%B %d, %Y')],
        ["Report ID", report_id],
    ]
    story.append(_make_kv_table(cover_data))
    story.append(Spacer(1, 16))

    # "Prepared by" callout box
    prep_html = (
        '<font color="#D4A017"><b>Prepared by West Egg Development</b></font><br/>'
        '<font size="8" color="#666666">Automated Zoning Feasibility Analysis Engine</font>'
    )
    prep_p = Paragraph(prep_html, ParagraphStyle(
        'PrepBy', fontSize=10, alignment=TA_CENTER, leading=14,
    ))
    prep_t = Table([[prep_p]], colWidths=[CONTENT_W])
    prep_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GOLD_LIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 1, GOLD),
    ]))
    story.append(prep_t)
    story.append(PageBreak())


# ──────────────────────────────────────────────────────────────────
# SECTION 2: PROPERTY MAPS
# ──────────────────────────────────────────────────────────────────

def _build_property_maps(story, styles, lot, map_images):
    """Section 2: Satellite and street map images."""
    has_satellite = map_images and map_images.get("satellite_bytes")
    has_street = map_images and map_images.get("street_bytes")
    has_geometry = lot.geometry is not None

    if not has_satellite and not has_street and not has_geometry:
        return

    story.append(_section_header("Property Maps", section_num=2, styles=styles))
    story.append(Spacer(1, 6))

    if has_satellite:
        try:
            story.append(Paragraph("Satellite View with Lot Boundary", styles['SubSection']))
            img = _image_from_bytes(map_images["satellite_bytes"], CONTENT_W, 4.0 * inch)
            story.append(img)
            story.append(Paragraph(
                "Lot boundary outlined in blue. Source: ESRI World Imagery.",
                styles['NoteText'],
            ))
            story.append(Spacer(1, 8))
        except Exception:
            pass

    if has_street:
        try:
            story.append(Paragraph("Street Map Context", styles['SubSection']))
            img = _image_from_bytes(map_images["street_bytes"], CONTENT_W, 3.5 * inch)
            story.append(img)
            story.append(Paragraph(
                "Lot boundary outlined in blue. Source: ESRI / OpenStreetMap.",
                styles['NoteText'],
            ))
            story.append(Spacer(1, 8))
        except Exception:
            pass

    # Zoomed-out context map (neighbourhood / half-borough scale)
    has_context = map_images and map_images.get("context_map_bytes")
    if has_context:
        try:
            story.append(Paragraph("Neighbourhood Context Map", styles['SubSection']))
            img = _image_from_bytes(map_images["context_map_bytes"], CONTENT_W, 3.0 * inch)
            story.append(img)
            story.append(Paragraph(
                "Zoomed-out view showing property location within the borough. "
                "Red marker indicates subject property. Source: ESRI.",
                styles['NoteText'],
            ))
            story.append(Spacer(1, 8))
        except Exception:
            pass

    # Fallback: programmatic lot diagram
    if not has_satellite and not has_street and has_geometry:
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
    story.append(_section_header("Key Development Features", section_num=4, styles=styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Important zoning characteristics and development features for this site:",
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

    col_w = CONTENT_W / 2 - 2
    t = Table(rows, colWidths=[col_w, col_w])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), FEATURE_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, GRID_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBEFORE', (0, 0), (0, -1), 3, GOLD),
        ('LINEBEFORE', (1, 0), (1, -1), 3, GOLD),
    ]))
    story.append(t)


# ──────────────────────────────────────────────────────────────────
# SECTION 5: ZONING OVERVIEW  (with zoning map)
# ──────────────────────────────────────────────────────────────────

def _build_zoning_overview(story, styles, lot, env, map_images=None):
    """Section 5: Zoning districts, overlays, FAR, height/setback, and optional zoning map."""
    story.append(_section_header("Zoning Overview", section_num=5, styles=styles))
    story.append(Spacer(1, 6))

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
    story.append(_section_header("Detailed Calculations", section_num=6, styles=styles))
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

def _build_development_scenarios(story, styles, scenarios, massing_models=None):
    """Section 7: Individual scenarios with full program and optional 3D massing images."""
    story.append(PageBreak())
    story.append(_section_header("Development Scenarios", section_num=7, styles=styles))
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
        # ── Scenario header (gold accent bar) ──
        sc_head = Paragraph(
            f"<b>Scenario {i+1}: {scenario.name}</b>",
            ParagraphStyle('ScHead', fontSize=11, fontName='Helvetica-Bold',
                           textColor=DARK, leading=14),
        )
        sc_bar = Table([[sc_head]], colWidths=[CONTENT_W])
        sc_bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GOLD_LIGHT),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('LINEBEFORE', (0, 0), (0, -1), 3, GOLD),
        ]))
        story.append(sc_bar)
        story.append(Spacer(1, 2))
        story.append(Paragraph(scenario.description, styles['SmallBody']))
        story.append(Spacer(1, 3))

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
        "Side-by-side comparison of all development scenarios analyzed:",
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
        ('BACKGROUND', (0, 0), (-1, 0), BLUE_DARK),
        ('TEXTCOLOR', (0, 1), (0, -1), GREY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('GRID', (0, 0), (-1, -1), 0.5, GRID_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
    ]
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
    story.append(Spacer(1, 12))
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
        2.2 * inch, 0.9 * inch, 0.9 * inch, 0.8 * inch, 0.8 * inch,
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
    """Section 11: Notes & Disclaimers (no dollar / valuation references)."""
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
    story.append(Spacer(1, 6))
    story.append(_section_header("Notes & Disclaimers", section_num=11, styles=styles))
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
        topMargin=1.0 * inch, bottomMargin=0.75 * inch,
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

    # 7. Development scenarios (with 3D massing)
    _build_development_scenarios(story, styles, result.scenarios,
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
        topMargin=1.0 * inch, bottomMargin=0.75 * inch,
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
    _build_development_scenarios(story, styles, result.scenarios, massing_models=massing_models)
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
    return codes.get(code, f"Code {code}")


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
