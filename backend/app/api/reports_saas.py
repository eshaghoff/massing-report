"""SaaS report endpoints — preview, generate, list, get, download PDF."""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.api.auth import get_current_user, get_optional_user, UserInfo
from app.services.pricing import calculate_price
from app.config import settings

# ── Zoning engine imports ──
from app.services.geocoding import geocode_address, parse_address
from app.services.pluto import fetch_pluto_data
from app.services.geometry import fetch_lot_geometry, fetch_zoning_layers
from app.services.report import generate_report
from app.services.street_width import determine_street_width
from app.services.maps import (
    fetch_satellite_image, fetch_street_map_image,
    fetch_zoning_map_image, fetch_context_map_image,
)
from app.zoning_engine.calculator import ZoningCalculator
from app.zoning_engine.massing import compute_massing_geometry
from app.zoning_engine.massing_builder import build_massing_model
from app.zoning_engine.building_program import generate_building_program
from app.zoning_engine.parking_layout import evaluate_parking_layouts
from app.zoning_engine.valuation import rank_scenarios
from app.models.schemas import CalculationResult, SpecialDistrictInfo

router = APIRouter(prefix="/api/v1/saas/reports", tags=["saas-reports"])
calculator = ZoningCalculator()

# ── In-memory store (replace with DB later) ──
_reports: dict[str, dict] = {}
_preview_cache: dict[str, dict] = {}


# ── Request / Response models ──
class PreviewRequest(BaseModel):
    address: Optional[str] = None
    bbl: Optional[str] = None


class GenerateRequest(BaseModel):
    address: Optional[str] = None
    bbl: Optional[str] = None
    preview_id: Optional[str] = None  # reuse cached preview


class ReportSummary(BaseModel):
    id: str
    bbl: str
    address: str
    status: str  # pending | processing | completed | failed
    buildable_sf: Optional[float] = None
    price_cents: Optional[int] = None
    created_at: str
    scenarios_count: Optional[int] = None


# ── Helper: run the zoning analysis (no PDF) ──
async def _run_analysis(address: str = None, bbl: str = None):
    """Run the full zoning analysis pipeline, returning structured data."""
    from app.api.routes import _build_lot_profile
    from app.models.schemas import LotProfile

    # Resolve BBL
    if address:
        try:
            bbl_result = await geocode_address(address)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Geocoding error: {e}")
    elif bbl:
        from app.services.geocoding import parse_bbl
        from app.models.schemas import BBLResponse
        parsed = parse_bbl(bbl)
        if not parsed:
            raise HTTPException(status_code=400, detail=f"Invalid BBL: {bbl}")
        bbl_result = BBLResponse(
            bbl=parsed, borough=int(parsed[0]),
            block=int(parsed[1:6]), lot=int(parsed[6:10]),
        )
    else:
        raise HTTPException(status_code=400, detail="Provide address or bbl.")

    resolved_bbl = bbl_result.bbl

    # Fetch PLUTO
    pluto = await fetch_pluto_data(resolved_bbl, settings.socrata_app_token)
    if not pluto:
        raise HTTPException(status_code=404, detail=f"No PLUTO data for BBL {resolved_bbl}")

    # Fetch geometry + zoning layers
    geometry = None
    zoning_layers = None
    try:
        geometry = await fetch_lot_geometry(resolved_bbl)
    except Exception:
        pass
    try:
        zoning_layers = await fetch_zoning_layers(resolved_bbl)
    except Exception:
        pass

    lot_profile = await _build_lot_profile(bbl_result, pluto, geometry, zoning_layers)

    # Zoning calc
    try:
        calc_result = calculator.calculate(lot_profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Zoning calculation error: {e}")

    zoning_envelope = calc_result["zoning_envelope"]
    scenarios = calc_result["scenarios"]

    # Massing geometry
    primary_district = lot_profile.zoning_districts[0] if lot_profile.zoning_districts else ""
    if geometry:
        for scenario in scenarios:
            massing = compute_massing_geometry(
                geometry, zoning_envelope, scenario.floors,
                district=primary_district,
            )
            scenario.massing_geometry = massing

    return {
        "bbl_result": bbl_result,
        "lot_profile": lot_profile,
        "calc_result": calc_result,
        "zoning_envelope": zoning_envelope,
        "scenarios": scenarios,
        "geometry": geometry,
        "primary_district": primary_district,
    }


# ── POST /preview ──
@router.post("/preview")
async def preview_report(req: PreviewRequest, user: UserInfo | None = Depends(get_optional_user)):
    """Run zoning analysis (no PDF) and return summary + price quote."""
    analysis = await _run_analysis(address=req.address, bbl=req.bbl)

    lot = analysis["lot_profile"]
    envelope = analysis["zoning_envelope"]
    scenarios = analysis["scenarios"]

    # Buildable SF = max ZFA across scenarios (for display)
    max_zfa = max((s.zoning_floor_area or s.total_gross_sf or 0) for s in scenarios) if scenarios else 0
    buildable_sf = max_zfa

    # Billing SF = lot_area × max(residential_far, commercial_far) — excludes CF FAR
    lot_area = lot.lot_area or 0
    billing_far = max(envelope.residential_far or 0, envelope.commercial_far or 0)
    billing_sf = lot_area * billing_far

    # Calculate price based on billing SF (not raw max ZFA)
    pricing = calculate_price(billing_sf)

    # Build scenario summaries
    scenario_summaries = []
    for s in scenarios:
        scenario_summaries.append({
            "name": s.name,
            "total_zfa": s.zoning_floor_area,
            "max_height_ft": s.max_height_ft,
            "num_floors": s.num_floors,
            "total_units": s.total_units,
            "residential_sf": s.residential_sf,
            "commercial_sf": s.commercial_sf,
            "far_used": s.far_used,
        })

    # Cache for later generate
    preview_id = str(uuid.uuid4())
    _preview_cache[preview_id] = {
        "analysis": analysis,
        "pricing": pricing,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user.clerk_user_id if user else "anonymous",
    }

    resolved_address = lot.address or req.address or req.bbl or ""

    return {
        "preview_id": preview_id,
        "bbl": lot.bbl,
        "address": resolved_address,
        "borough": lot.borough,
        "lot_area": lot.lot_area,
        "lot_frontage": lot.lot_frontage,
        "lot_depth": lot.lot_depth,
        "zoning_districts": lot.zoning_districts,
        "buildable_sf": buildable_sf,
        "scenarios": scenario_summaries,
        "pricing": pricing,
        "zoning_envelope": {
            "residential_far": envelope.residential_far,
            "commercial_far": envelope.commercial_far,
            "cf_far": envelope.cf_far,
            "max_building_height": envelope.max_building_height,
            "lot_coverage_max": envelope.lot_coverage_max,
            "quality_housing": envelope.quality_housing,
        },
    }


# ── POST /generate ──
@router.post("/generate")
async def generate_report_endpoint(
    req: GenerateRequest,
    background_tasks: BackgroundTasks,
    user: UserInfo = Depends(get_current_user),
):
    """Generate a full PDF report. Returns report ID for polling."""
    report_id = str(uuid.uuid4())

    # Create report record
    _reports[report_id] = {
        "id": report_id,
        "user_id": user.clerk_user_id if user else "anonymous",
        "bbl": "",
        "address": req.address or req.bbl or "",
        "status": "processing",
        "buildable_sf": None,
        "price_cents": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pdf_path": None,
        "scenarios_count": None,
        "analysis_json": None,
    }

    background_tasks.add_task(
        _generate_report_task, report_id, req, user
    )

    return {"report_id": report_id, "status": "processing"}


async def _generate_report_task(report_id: str, req: GenerateRequest, user: UserInfo):
    """Background task: run full analysis + generate PDF."""
    try:
        # Check if we have a cached preview
        analysis = None
        if req.preview_id and req.preview_id in _preview_cache:
            cached = _preview_cache[req.preview_id]
            if cached["user_id"] == user.clerk_user_id or cached["user_id"] == "anonymous":
                analysis = cached["analysis"]

        if analysis is None:
            analysis = await _run_analysis(address=req.address, bbl=req.bbl)

        lot_profile = analysis["lot_profile"]
        calc_result = analysis["calc_result"]
        zoning_envelope = analysis["zoning_envelope"]
        scenarios = analysis["scenarios"]
        geometry = analysis["geometry"]
        primary_district = analysis["primary_district"]

        # Building programs
        building_programs = []
        for scenario in scenarios:
            scenario_dict = {
                "total_gross_sf": scenario.total_gross_sf,
                "zoning_floor_area": scenario.zoning_floor_area or scenario.total_gross_sf,
                "residential_sf": scenario.residential_sf,
                "commercial_sf": scenario.commercial_sf,
                "cf_sf": scenario.cf_sf,
                "total_units": scenario.total_units,
                "num_floors": scenario.num_floors,
                "max_height_ft": scenario.max_height_ft,
                "floors": [f.dict() for f in scenario.floors] if scenario.floors else [],
            }
            bp = generate_building_program(
                scenario_dict,
                lot_depth=lot_profile.lot_depth or 100,
                lot_frontage=lot_profile.lot_frontage or 50,
                borough=lot_profile.borough,
            )
            building_programs.append(bp.to_dict())

        # Parking
        parking_layout_result = None
        scenarios_with_parking = [s for s in scenarios if s.parking and s.parking.total_spaces_required > 0]
        if scenarios_with_parking:
            max_parking = max(scenarios_with_parking, key=lambda s: s.parking.total_spaces_required)
            footprint = (lot_profile.lot_area or 5000) * (
                zoning_envelope.lot_coverage_max / 100 if zoning_envelope.lot_coverage_max else 0.65
            )
            parking_layout_result = evaluate_parking_layouts(
                required_spaces=max_parking.parking.total_spaces_required,
                lot_area=lot_profile.lot_area or 5000,
                building_footprint=footprint,
                typical_floor_sf=footprint,
                lot_frontage=lot_profile.lot_frontage or 50,
                lot_depth=lot_profile.lot_depth or 100,
                is_quality_housing=zoning_envelope.quality_housing,
                waiver_eligible=max_parking.parking.waiver_eligible,
            )

        # Map images
        map_images = None
        lat = lot_profile.latitude
        lng = lot_profile.longitude
        lot_geom = lot_profile.geometry
        if lat and lng:
            sat, street, zmap, ctx = await asyncio.gather(
                fetch_satellite_image(lat, lng, lot_geom),
                fetch_street_map_image(lat, lng, lot_geom),
                fetch_zoning_map_image(lat, lng, lot_geom),
                fetch_context_map_image(lat, lng, lot_geom),
            )
            if any([sat, street, zmap, ctx]):
                map_images = {
                    "satellite_bytes": sat,
                    "street_bytes": street,
                    "zoning_map_bytes": zmap,
                    "context_map_bytes": ctx,
                }

        # Massing models
        massing_models = {}
        for scenario in scenarios:
            try:
                model = build_massing_model(
                    lot=lot_profile,
                    scenario=scenario,
                    envelope=zoning_envelope,
                    district=primary_district,
                    lot_geojson=lot_geom,
                )
                if model and "error" not in model:
                    massing_models[scenario.name] = model
            except Exception:
                pass

        # Build CalculationResult for report generator
        result_obj = CalculationResult(
            lot_profile=lot_profile,
            zoning_envelope=zoning_envelope,
            scenarios=scenarios,
            building_type=calc_result.get("building_type"),
            street_wall=calc_result.get("street_wall"),
            special_districts=(
                SpecialDistrictInfo(**calc_result["special_districts"])
                if calc_result.get("special_districts") else None
            ),
            city_of_yes=calc_result.get("city_of_yes"),
        )

        # Generate PDF
        pdf_path = generate_report(
            result_obj,
            parking_layout_result=parking_layout_result,
            assemblage_data=None,
            map_images=map_images,
            massing_models=massing_models,
        )

        # Pricing — billing SF = lot_area × max(res_far, comm_far), excludes CF
        lot_area_val = lot_profile.lot_area or 0
        billing_far = max(zoning_envelope.residential_far or 0, zoning_envelope.commercial_far or 0)
        billing_sf = lot_area_val * billing_far
        pricing = calculate_price(billing_sf)

        # Update record
        _reports[report_id].update({
            "bbl": lot_profile.bbl,
            "address": lot_profile.address or "",
            "status": "completed",
            "buildable_sf": billing_sf,
            "price_cents": pricing["price_cents"],
            "pdf_path": pdf_path,
            "scenarios_count": len(scenarios),
        })

    except Exception as e:
        _reports[report_id]["status"] = "failed"
        _reports[report_id]["error"] = str(e)


# ── GET / — list user reports ──
@router.get("/")
async def list_reports(user: UserInfo = Depends(get_current_user)):
    """List all reports for the authenticated user."""
    user_reports = [
        ReportSummary(
            id=r["id"],
            bbl=r["bbl"],
            address=r["address"],
            status=r["status"],
            buildable_sf=r.get("buildable_sf"),
            price_cents=r.get("price_cents"),
            created_at=r["created_at"],
            scenarios_count=r.get("scenarios_count"),
        )
        for r in _reports.values()
        if r["user_id"] == user.clerk_user_id
    ]
    # Sort newest first
    user_reports.sort(key=lambda r: r.created_at, reverse=True)
    return {"reports": [r.dict() for r in user_reports]}


# ── GET /{report_id} ──
@router.get("/{report_id}")
async def get_report(report_id: str, user: UserInfo = Depends(get_current_user)):
    """Get report metadata + status (for polling)."""
    report = _reports.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report["user_id"] != user.clerk_user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": report["id"],
        "bbl": report["bbl"],
        "address": report["address"],
        "status": report["status"],
        "buildable_sf": report.get("buildable_sf"),
        "price_cents": report.get("price_cents"),
        "created_at": report["created_at"],
        "scenarios_count": report.get("scenarios_count"),
        "error": report.get("error"),
    }


# ── GET /{report_id}/pdf ──
@router.get("/{report_id}/pdf")
async def download_report_pdf(report_id: str, user: UserInfo = Depends(get_current_user)):
    """Download the generated PDF report."""
    from fastapi.responses import FileResponse

    report = _reports.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report["user_id"] != user.clerk_user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if report["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Report status: {report['status']}")

    pdf_path = report.get("pdf_path")
    if not pdf_path or not os.path.isfile(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    filename = f"zoning-report-{report['bbl']}.pdf"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
    )
