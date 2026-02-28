from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from app.models.schemas import (
    LotProfile, CalculationResult, AssemblageRequest, ReportRequest,
    SpecialDistrictInfo,

    ProgramsSummary, ProgramApplicability,
)
import asyncio

from app.services.geocoding import geocode_address, parse_address, BOROUGH_CODE_TO_NAME
from app.services.pluto import fetch_pluto_data
from app.services.geometry import fetch_lot_geometry, fetch_zoning_layers
from app.services.report import generate_report, generate_report_bytes
from app.services.street_width import determine_street_width
from app.services.maps import fetch_satellite_image, fetch_street_map_image, fetch_zoning_map_image, fetch_context_map_image
from app.zoning_engine.calculator import ZoningCalculator
from app.zoning_engine.massing import compute_massing_geometry
from app.zoning_engine.massing_builder import build_massing_model
from app.zoning_engine.building_program import generate_building_program
from app.zoning_engine.parking_layout import evaluate_parking_layouts
from app.zoning_engine.assemblage import analyze_assemblage, AssemblageAnalysis
from app.zoning_engine.valuation import rank_scenarios
from app.config import settings

router = APIRouter(prefix="/api")
calculator = ZoningCalculator()

# Default calculation options (can be overridden per-request)
_DEFAULT_CALC_OPTIONS = {
    "include_cellar": True,
    "include_inclusionary": False,
}



def _build_programs_summary(calc_result: dict):
    """Convert raw program results from calculator into ProgramsSummary schema."""
    programs_data = calc_result.get("programs")
    if not programs_data:
        return None
    raw_results = programs_data.get("results", [])
    effects = programs_data.get("effects_summary", {})

    all_progs = []
    for r in raw_results:
        all_progs.append(ProgramApplicability(
            program_key=r.program_key,
            program_name=r.program_name,
            category=r.category.value if hasattr(r.category, 'value') else str(r.category),
            applicable=r.applicable,
            eligible=r.eligible,
            far_bonus=r.effect.far_bonus if r.effect else 0,
            height_bonus_ft=r.effect.height_bonus_ft if r.effect else 0,
            parking_reduction_pct=r.effect.parking_reduction_pct if r.effect else 0,
            description=r.effect.description if r.effect else "",
            reason=r.reason,
            source_zr=r.source_zr,
            details=r.effect.details if r.effect else {},
        ))

    applicable = [p for p in all_progs if p.applicable]

    return ProgramsSummary(
        programs=all_progs,
        applicable_programs=applicable,
        total_far_bonus=effects.get("total_far_bonus", 0),
        total_height_bonus_ft=effects.get("total_height_bonus_ft", 0),
        use_restrictions=effects.get("use_restrictions", []),
        mandatory_affordable_pct=effects.get("mandatory_affordable_pct", 0),
    )

@router.get("/lookup")
async def lookup_address(address: str = Query(..., description="NYC street address")):
    """Look up a NYC address and return full lot profile with zoning analysis."""
    # Step 1: Geocode address to BBL
    try:
        bbl_result = await geocode_address(address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Geocoding service error: {e}")

    # Step 2: Fetch PLUTO data
    pluto = await fetch_pluto_data(bbl_result.bbl, settings.socrata_app_token)
    if not pluto:
        raise HTTPException(status_code=404, detail=f"No PLUTO data found for BBL {bbl_result.bbl}")

    # Step 3: Fetch lot geometry
    geometry = await fetch_lot_geometry(bbl_result.bbl)

    # Step 4: Fetch zoning layers
    zoning_layers = await fetch_zoning_layers(bbl_result.bbl)

    # Build lot profile
    lot_profile = await _build_lot_profile(bbl_result, pluto, geometry, zoning_layers)

    # Step 5: Run zoning calculations
    try:
        result = calculator.calculate(lot_profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Step 6: Generate massing geometry for each scenario
    primary_district = lot_profile.zoning_districts[0] if lot_profile.zoning_districts else ""
    if geometry:
        for scenario in result["scenarios"]:
            massing = compute_massing_geometry(
                geometry, result["zoning_envelope"], scenario.floors,
                district=primary_district,
            )
            scenario.massing_geometry = massing

    return CalculationResult(
        lot_profile=lot_profile,
        zoning_envelope=result["zoning_envelope"],
        scenarios=result["scenarios"],
        building_type=result.get("building_type"),
        street_wall=result.get("street_wall"),
        special_districts=SpecialDistrictInfo(**result["special_districts"]) if result.get("special_districts") else None,
        city_of_yes=result.get("city_of_yes"),
            programs=_build_programs_summary(result),
    )


@router.get("/lot/{bbl}")
async def get_lot(bbl: str):
    """Get cached lot data by BBL."""
    pluto = await fetch_pluto_data(bbl, settings.socrata_app_token)
    if not pluto:
        raise HTTPException(status_code=404, detail=f"No data found for BBL {bbl}")

    geometry = await fetch_lot_geometry(bbl)
    zoning_layers = await fetch_zoning_layers(bbl)

    from app.models.schemas import BBLResponse
    bbl_result = BBLResponse(
        bbl=bbl,
        borough=int(bbl[0]),
        block=int(bbl[1:6]),
        lot=int(bbl[6:10]),
    )
    lot_profile = await _build_lot_profile(bbl_result, pluto, geometry, zoning_layers)

    return lot_profile


@router.post("/calculate")
async def calculate_zoning(lot_profile: LotProfile):
    """Run zoning calculations for a given lot profile."""
    try:
        result = calculator.calculate(lot_profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    primary_district = lot_profile.zoning_districts[0] if lot_profile.zoning_districts else ""
    if lot_profile.geometry:
        for scenario in result["scenarios"]:
            massing = compute_massing_geometry(
                lot_profile.geometry, result["zoning_envelope"], scenario.floors,
                district=primary_district,
            )
            scenario.massing_geometry = massing

    return CalculationResult(
        lot_profile=lot_profile,
        zoning_envelope=result["zoning_envelope"],
        scenarios=result["scenarios"],
        building_type=result.get("building_type"),
        street_wall=result.get("street_wall"),
        special_districts=SpecialDistrictInfo(**result["special_districts"]) if result.get("special_districts") else None,
        city_of_yes=result.get("city_of_yes"),
            programs=_build_programs_summary(result),
    )


@router.get("/massing/{bbl}")
async def get_massing(bbl: str):
    """Get 3D massing geometries for a BBL."""
    pluto = await fetch_pluto_data(bbl, settings.socrata_app_token)
    if not pluto:
        raise HTTPException(status_code=404, detail=f"No data found for BBL {bbl}")

    geometry = await fetch_lot_geometry(bbl)
    if not geometry:
        raise HTTPException(status_code=404, detail=f"No geometry found for BBL {bbl}")

    zoning_layers = await fetch_zoning_layers(bbl)

    from app.models.schemas import BBLResponse
    bbl_result = BBLResponse(
        bbl=bbl,
        borough=int(bbl[0]),
        block=int(bbl[1:6]),
        lot=int(bbl[6:10]),
    )
    lot_profile = await _build_lot_profile(bbl_result, pluto, geometry, zoning_layers)

    result = calculator.calculate(lot_profile)

    primary_district = lot_profile.zoning_districts[0] if lot_profile.zoning_districts else ""
    massing_results = []
    for scenario in result["scenarios"]:
        massing = compute_massing_geometry(
            geometry, result["zoning_envelope"], scenario.floors,
            district=primary_district,
        )
        massing_results.append({
            "scenario_name": scenario.name,
            "massing": massing,
            "scenario": scenario,
        })

    return massing_results


@router.post("/assemblage")
async def create_assemblage(request: AssemblageRequest):
    """Merge multiple lots and recalculate development potential."""
    if len(request.bbls) < 2:
        raise HTTPException(status_code=400, detail="Assemblage requires at least 2 BBLs.")

    # Fetch all lots
    lots_data = []
    for bbl in request.bbls:
        pluto = await fetch_pluto_data(bbl, settings.socrata_app_token)
        geometry = await fetch_lot_geometry(bbl)
        if pluto:
            lots_data.append({"bbl": bbl, "pluto": pluto, "geometry": geometry})

    if len(lots_data) < 2:
        raise HTTPException(status_code=404, detail="Could not find data for enough lots.")

    # Merge geometries
    from shapely.geometry import shape
    from shapely.ops import unary_union
    import json

    polygons = []
    total_lot_area = 0
    total_frontage = 0
    total_depth = 0

    for lot_data in lots_data:
        if lot_data["geometry"]:
            poly = shape(lot_data["geometry"])
            polygons.append(poly)
        if lot_data["pluto"].lotarea:
            total_lot_area += lot_data["pluto"].lotarea
        if lot_data["pluto"].lotfront:
            total_frontage = max(total_frontage, lot_data["pluto"].lotfront)
        if lot_data["pluto"].lotdepth:
            total_depth = max(total_depth, lot_data["pluto"].lotdepth)

    merged_geom = None
    if polygons:
        merged = unary_union(polygons)
        merged_geom = json.loads(json.dumps(merged.__geo_interface__))

    # Use first lot's zoning as primary
    primary = lots_data[0]
    zoning_layers = await fetch_zoning_layers(primary["bbl"])

    from app.models.schemas import BBLResponse
    bbl_result = BBLResponse(
        bbl=primary["bbl"],
        borough=int(primary["bbl"][0]),
        block=int(primary["bbl"][1:6]),
        lot=int(primary["bbl"][6:10]),
    )

    lot_profile = await _build_lot_profile(bbl_result, primary["pluto"], merged_geom, zoning_layers)
    lot_profile.lot_area = total_lot_area
    lot_profile.lot_frontage = total_frontage
    lot_profile.lot_depth = total_depth

    result = calculator.calculate(lot_profile)

    primary_district = lot_profile.zoning_districts[0] if lot_profile.zoning_districts else ""
    if merged_geom:
        for scenario in result["scenarios"]:
            massing = compute_massing_geometry(
                merged_geom, result["zoning_envelope"], scenario.floors,
                district=primary_district,
            )
            scenario.massing_geometry = massing

    # Also calculate individual lot potentials for comparison
    individual_totals = {"total_zfa": 0, "total_units": 0}
    for lot_data in lots_data:
        if lot_data["pluto"].lotarea and lot_data["pluto"].residfar:
            individual_totals["total_zfa"] += (
                lot_data["pluto"].lotarea * lot_data["pluto"].residfar
            )

    return {
        "assemblage": CalculationResult(
            lot_profile=lot_profile,
            zoning_envelope=result["zoning_envelope"],
            scenarios=result["scenarios"],
            building_type=result.get("building_type"),
            street_wall=result.get("street_wall"),
            special_districts=SpecialDistrictInfo(**result["special_districts"]) if result.get("special_districts") else None,
            city_of_yes=result.get("city_of_yes"),
            programs=_build_programs_summary(result),
        ),
        "individual_lots": lots_data,
        "individual_totals": individual_totals,
        "assemblage_benefit": {
            "additional_zfa": (
                result["zoning_envelope"].max_residential_zfa or 0
            ) - individual_totals["total_zfa"],
        },
    }


@router.post("/report")
async def create_report(request: ReportRequest):
    """Generate a PDF feasibility report."""
    pluto = await fetch_pluto_data(request.bbl, settings.socrata_app_token)
    if not pluto:
        raise HTTPException(status_code=404, detail=f"No data found for BBL {request.bbl}")

    geometry = await fetch_lot_geometry(request.bbl)
    zoning_layers = await fetch_zoning_layers(request.bbl)

    from app.models.schemas import BBLResponse
    bbl_result = BBLResponse(
        bbl=request.bbl,
        borough=int(request.bbl[0]),
        block=int(request.bbl[1:6]),
        lot=int(request.bbl[6:10]),
    )
    lot_profile = await _build_lot_profile(bbl_result, pluto, geometry, zoning_layers)

    calc_result = calculator.calculate(lot_profile)

    result = CalculationResult(
        lot_profile=lot_profile,
        zoning_envelope=calc_result["zoning_envelope"],
        scenarios=calc_result["scenarios"],
        building_type=calc_result.get("building_type"),
        street_wall=calc_result.get("street_wall"),
        special_districts=SpecialDistrictInfo(**calc_result["special_districts"]) if calc_result.get("special_districts") else None,
        city_of_yes=calc_result.get("city_of_yes"),
        programs=_build_programs_summary(calc_result),
    )

    # Fetch map images for the report
    map_images = None
    lat = lot_profile.latitude
    lng = lot_profile.longitude
    if lat and lng:
        satellite_bytes, street_bytes = await asyncio.gather(
            fetch_satellite_image(lat, lng, geometry),
            fetch_street_map_image(lat, lng, geometry),
        )
        if satellite_bytes or street_bytes:
            map_images = {
                "satellite_bytes": satellite_bytes,
                "street_bytes": street_bytes,
            }

    # Rank scenarios by estimated value
    valuation_rankings = rank_scenarios(calc_result["scenarios"], lot_profile.borough)

    filepath = generate_report(
        result,
        map_images=map_images,
        valuation_rankings=valuation_rankings,
    )
    return {"report_path": filepath, "bbl": request.bbl}


@router.get("/report/{bbl}/download")
async def download_report(bbl: str):
    """Download a previously generated report."""
    import glob as globlib
    output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "output")
    pattern = os.path.join(output_dir, f"zoning_feasibility_{bbl}_*.pdf")
    files = sorted(globlib.glob(pattern), reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail="No report found for this BBL. Generate one first.")
    return FileResponse(
        files[0],
        media_type="application/pdf",
        filename=os.path.basename(files[0]),
    )


from pydantic import BaseModel as PydanticBaseModel
from typing import Optional as Opt
from app.services.geocoding import parse_bbl, validate_bbl
from app.models.schemas import BBLResponse


# ──────────────────────────────────────────────────────────────
# MASSING ENDPOINT
# ──────────────────────────────────────────────────────────────

@router.get("/v1/massing/{bbl}")
async def get_massing(
    bbl: str,
    scenario: Opt[str] = None,
):
    """Get floor-by-floor massing model for a lot.

    Returns detailed massing data for Three.js rendering.
    Optionally filter to a specific scenario name.
    """
    parsed = parse_bbl(bbl)
    if not parsed:
        raise HTTPException(status_code=400, detail=f"Invalid BBL: {bbl}")
    bbl = parsed

    pluto = await fetch_pluto_data(bbl, settings.socrata_app_token)
    if not pluto:
        raise HTTPException(status_code=404, detail=f"No PLUTO data for BBL {bbl}")

    geometry = await fetch_lot_geometry(bbl)
    zoning_layers = await fetch_zoning_layers(bbl)

    bbl_result = BBLResponse(
        bbl=bbl, borough=int(bbl[0]),
        block=int(bbl[1:6]), lot=int(bbl[6:10]),
    )
    lot_profile = await _build_lot_profile(bbl_result, pluto, geometry, zoning_layers)

    calc_result = calculator.calculate(lot_profile, options={
        "include_cellar": getattr(request, "include_cellar", True),
        "include_inclusionary": getattr(request, "include_inclusionary", False),
    })
    zoning_envelope = calc_result["zoning_envelope"]
    scenarios = calc_result["scenarios"]
    district = lot_profile.zoning_districts[0] if lot_profile.zoning_districts else ""

    # Filter to requested scenario if specified
    if scenario:
        scenarios = [s for s in scenarios if s.name.lower() == scenario.lower()]
        if not scenarios:
            raise HTTPException(
                status_code=404,
                detail=f"Scenario '{scenario}' not found. "
                       f"Available: {[s.name for s in calc_result['scenarios']]}",
            )

    # Build massing model for each scenario
    massing_models = []
    for sc in scenarios:
        model = build_massing_model(
            lot=lot_profile,
            scenario=sc,
            envelope=zoning_envelope,
            district=district,
            lot_geojson=geometry,
        )
        massing_models.append(model)

    # Return combined response (first scenario's lot data + all scenario massings)
    if not massing_models:
        raise HTTPException(status_code=404, detail="No scenarios could be built")

    result = massing_models[0]
    if len(massing_models) > 1:
        result["scenarios"] = []
        for m in massing_models:
            result["scenarios"].extend(m.get("scenarios", []))

    return result


# ──────────────────────────────────────────────────────────────
# FULL ANALYSIS ENDPOINT
# ──────────────────────────────────────────────────────────────

class FullAnalysisRequest(PydanticBaseModel):
    """Request for full end-to-end analysis."""
    address: Opt[str] = None
    bbl: Opt[str] = None
    bbls: Opt[list[str]] = None  # for assemblage
    addresses: Opt[list[str]] = None  # for assemblage by addresses
    include_cellar: bool = True       # Include cellar space (checked by default)
    include_inclusionary: bool = False  # Include IH/UAP scenarios (unchecked by default)


@router.post("/v1/full-analysis")
async def full_analysis(
    request: FullAnalysisRequest,
    nocache: bool = False,
):
    """Full end-to-end analysis: lot → zoning → building program → parking → report.

    Accepts address, BBL, multiple BBLs (assemblage), or multiple addresses.
    Returns comprehensive analysis with all Phase 2 components.
    When multiple lots are provided, includes assemblage delta analysis.

    Query params:
        nocache: bypass Redis cache for fresh results
    """
    # ── Resolve all BBLs from the request ──
    # Store full BBLResponse objects to preserve lat/lng from geocoding
    bbl_responses: list[BBLResponse] = []

    if request.addresses and len(request.addresses) >= 2:
        # Multiple addresses → assemblage
        for addr in request.addresses:
            try:
                result = await geocode_address(addr)
                bbl_responses.append(result)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not geocode address '{addr}': {e}",
                )
    elif request.bbls and len(request.bbls) >= 2:
        # Multiple BBLs → assemblage
        for b in request.bbls:
            parsed = parse_bbl(b)
            if not parsed:
                raise HTTPException(status_code=400, detail=f"Invalid BBL: {b}")
            bbl_responses.append(BBLResponse(
                bbl=parsed, borough=int(parsed[0]),
                block=int(parsed[1:6]), lot=int(parsed[6:10]),
            ))
    elif request.address:
        try:
            bbl_result = await geocode_address(request.address)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Geocoding service error: {type(e).__name__}: {e}")
        bbl_responses.append(bbl_result)
    elif request.bbl:
        parsed = parse_bbl(request.bbl)
        if not parsed:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid BBL format: '{request.bbl}'. "
                       "Use 10 digits (e.g., 3046220022) or dash-separated (e.g., 3-04622-0022).",
            )
        bbl_responses.append(BBLResponse(
            bbl=parsed, borough=int(parsed[0]),
            block=int(parsed[1:6]), lot=int(parsed[6:10]),
        ))
    elif request.bbls and len(request.bbls) == 1:
        parsed = parse_bbl(request.bbls[0])
        bbl_str = parsed or request.bbls[0]
        bbl_responses.append(BBLResponse(
            bbl=bbl_str, borough=int(bbl_str[0]),
            block=int(bbl_str[1:6]), lot=int(bbl_str[6:10]),
        ))
    else:
        raise HTTPException(status_code=400, detail="Provide address, bbl, bbls, or addresses.")

    # ── Build LotProfile for each BBL ──
    lot_profiles = []
    for bbl_obj in bbl_responses:
        bbl = bbl_obj.bbl
        try:
            pluto = await fetch_pluto_data(bbl, settings.socrata_app_token)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"PLUTO error for {bbl}: {e}")
        if not pluto:
            raise HTTPException(status_code=404, detail=f"No PLUTO data for BBL {bbl}.")

        try:
            geometry = await fetch_lot_geometry(bbl)
        except Exception:
            geometry = None
        try:
            zoning_layers = await fetch_zoning_layers(bbl)
        except Exception:
            zoning_layers = None

        lp = await _build_lot_profile(bbl_obj, pluto, geometry, zoning_layers)
        lot_profiles.append(lp)

    # ── If assemblage (2+ lots), run assemblage analysis ──
    assemblage_result = None
    if len(lot_profiles) >= 2:
        try:
            assemblage_result = analyze_assemblage(lot_profiles, calculator)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Assemblage analysis error: {type(e).__name__}: {e}",
            )
        # Use the merged lot for the primary analysis
        lot_profile = assemblage_result.merged_lot
        bbl = lot_profile.bbl
    else:
        lot_profile = lot_profiles[0]
        bbl = lot_profile.bbl

    # Validate lot has necessary data
    warnings = []
    if not lot_profile.zoning_districts:
        warnings.append("No zoning district found in PLUTO. Results may be incomplete.")
    if not lot_profile.lot_area or lot_profile.lot_area == 0:
        warnings.append("Lot area is 0 or missing in PLUTO. Using default values.")
        lot_profile.lot_area = lot_profile.lot_area or 5000  # Fallback

    # Run zoning calculations
    calc_options = {
        "include_cellar": getattr(request, "include_cellar", True),
        "include_inclusionary": getattr(request, "include_inclusionary", False),
    }
    try:
        calc_result = calculator.calculate(lot_profile, options=calc_options)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Zoning calculation error: {type(e).__name__}: {e}")

    zoning_envelope = calc_result["zoning_envelope"]
    scenarios = calc_result["scenarios"]

    # Generate massing geometry
    primary_district = lot_profile.zoning_districts[0] if lot_profile.zoning_districts else ""
    if geometry:
        for scenario in scenarios:
            massing = compute_massing_geometry(
                geometry, zoning_envelope, scenario.floors,
                district=primary_district,
            )
            scenario.massing_geometry = massing

    # Building program for each scenario
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

    # Parking layout for representative scenario (highest parking requirement)
    parking_layout = None
    scenarios_with_parking = [s for s in scenarios if s.parking and s.parking.total_spaces_required > 0]
    if scenarios_with_parking:
        max_parking_scenario = max(scenarios_with_parking, key=lambda s: s.parking.total_spaces_required)
        building_footprint = (lot_profile.lot_area or 5000) * (
            zoning_envelope.lot_coverage_max / 100 if zoning_envelope.lot_coverage_max else 0.65
        )
        parking_layout_result = evaluate_parking_layouts(
            required_spaces=max_parking_scenario.parking.total_spaces_required,
            lot_area=lot_profile.lot_area or 5000,
            building_footprint=building_footprint,
            typical_floor_sf=building_footprint,
            lot_frontage=lot_profile.lot_frontage or 50,
            lot_depth=lot_profile.lot_depth or 100,
            is_quality_housing=zoning_envelope.quality_housing,
            waiver_eligible=max_parking_scenario.parking.waiver_eligible,
        )
        parking_layout = parking_layout_result.to_dict()

    # Build CalculationResult
    result = CalculationResult(
        lot_profile=lot_profile,
        zoning_envelope=zoning_envelope,
        scenarios=scenarios,
        building_type=calc_result.get("building_type"),
        street_wall=calc_result.get("street_wall"),
        special_districts=SpecialDistrictInfo(**calc_result["special_districts"]) if calc_result.get("special_districts") else None,
        city_of_yes=calc_result.get("city_of_yes"),
        programs=_build_programs_summary(calc_result),
    )

    # Fetch map images for the report (concurrent)
    map_images = None
    lat = lot_profile.latitude
    lng = lot_profile.longitude
    lot_geometry = lot_profile.geometry
    if lat and lng:
        satellite_bytes, street_bytes, zoning_map_bytes, context_map_bytes = await asyncio.gather(
            fetch_satellite_image(lat, lng, lot_geometry),
            fetch_street_map_image(lat, lng, lot_geometry),
            fetch_zoning_map_image(lat, lng, lot_geometry),
            fetch_context_map_image(lat, lng, lot_geometry),
        )
        if satellite_bytes or street_bytes or zoning_map_bytes or context_map_bytes:
            map_images = {
                "satellite_bytes": satellite_bytes,
                "street_bytes": street_bytes,
                "zoning_map_bytes": zoning_map_bytes,
                "context_map_bytes": context_map_bytes,
            }

    # Build detailed massing models for each scenario (for 3D rendering in report)
    massing_models = {}
    for scenario in scenarios:
        try:
            model = build_massing_model(
                lot=lot_profile,
                scenario=scenario,
                envelope=zoning_envelope,
                district=primary_district,
                lot_geojson=lot_geometry,
            )
            if model and "error" not in model:
                massing_models[scenario.name] = model
        except Exception as e:
            warnings.append(f"Massing model failed for '{scenario.name}': {e}")

    # Rank scenarios by estimated value (kept for API JSON response, not PDF)
    valuation_rankings = rank_scenarios(scenarios, lot_profile.borough)

    # Generate PDF report (include assemblage data if available)
    assemblage_data = assemblage_result.to_dict() if assemblage_result else None
    report_filepath = generate_report(
        result,
        parking_layout_result=parking_layout_result if parking_layout else None,
        assemblage_data=assemblage_data,
        map_images=map_images,
        massing_models=massing_models,
    )

    # Build comparison table
    comparison_table = {}
    if scenarios:
        for sc in scenarios:
            comparison_table[sc.name] = {
                "total_zfa": sc.zoning_floor_area,
                "max_height": sc.max_height_ft,
                "floors": sc.num_floors,
                "far_used": sc.far_used,
                "residential_sf": sc.residential_sf,
                "commercial_sf": sc.commercial_sf,
                "total_units": sc.total_units,
                "parking_spaces": sc.parking.total_spaces_required if sc.parking else 0,
                "loss_factor": sc.loss_factor.loss_factor_pct if sc.loss_factor else None,
            }

    response = {
        "lot": lot_profile,
        "zoning": {
            "envelope": zoning_envelope,
            "building_type": calc_result.get("building_type"),
            "street_wall": calc_result.get("street_wall"),
            "special_districts": calc_result.get("special_districts"),
            "city_of_yes": calc_result.get("city_of_yes"),
        },
        "scenarios": scenarios,
        "building_programs": building_programs,
        "parking_layout": parking_layout,
        "comparison_table": comparison_table,
        "valuation": valuation_rankings,
        "report_path": report_filepath,
    }

    # Include assemblage analysis if applicable
    if assemblage_result:
        response["assemblage"] = {
            "individual_lots": [l.dict() for l in assemblage_result.individual_lots],
            "merged_lot": assemblage_result.merged_lot.dict(),
            "delta": assemblage_result.delta.to_dict(),
            "key_unlocks": assemblage_result.delta.key_unlocks,
            "contiguity_validated": assemblage_result.contiguity_validated,
            "contiguity_method": assemblage_result.contiguity_method,
        }
        warnings.extend(assemblage_result.warnings)

    if warnings:
        response["warnings"] = warnings
    return response


@router.get("/v1/reports/{report_id}")
async def get_report_pdf(report_id: str):
    """Download a generated PDF report by report ID."""
    import glob as globlib
    output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "output")
    pattern = os.path.join(output_dir, f"*_{report_id}.pdf")
    files = sorted(globlib.glob(pattern), reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail=f"No report found with ID {report_id}.")
    return FileResponse(
        files[0],
        media_type="application/pdf",
        filename=os.path.basename(files[0]),
    )


async def _build_lot_profile(bbl_result, pluto, geometry, zoning_layers) -> LotProfile:
    """Construct a LotProfile from API data."""
    zoning_districts = []
    overlays = []
    special_districts = []

    if pluto:
        for zd in [pluto.zonedist1, pluto.zonedist2, pluto.zonedist3, pluto.zonedist4]:
            if zd and zd.strip():
                zoning_districts.append(zd.strip())
        for ov in [pluto.overlay1, pluto.overlay2]:
            if ov and ov.strip():
                overlays.append(ov.strip())
        for sp in [pluto.spdist1, pluto.spdist2, pluto.spdist3]:
            if sp and sp.strip():
                special_districts.append(sp.strip())

    # Determine lot type from geometry and lot dimensions
    lot_type = "interior"
    if pluto and pluto.irrlotcode and pluto.irrlotcode.strip() == "Y":
        lot_type = "irregular"

    # Determine street width — uses DCP Digital City Map (Carto) as primary
    # source, Geoclient API as secondary, heuristic as fallback.
    # ZR 12-10: "wide street" = mapped street width >= 75 ft.
    address = pluto.address if pluto else ""
    borough = bbl_result.borough
    house_number = ""
    street_name = ""
    if address:
        parts = address.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].replace("-", "").isdigit():
            house_number = parts[0]
            street_name = parts[1]
    borough_name = BOROUGH_CODE_TO_NAME.get(borough, "")

    # Pass coordinates from geocoding for spatial street width lookup
    lat = getattr(bbl_result, "latitude", None)
    lng = getattr(bbl_result, "longitude", None)

    street_width = await determine_street_width(
        address=address,
        borough=borough,
        house_number=house_number,
        street_name=street_name,
        borough_name=borough_name,
        latitude=lat,
        longitude=lng,
    )

    return LotProfile(
        bbl=bbl_result.bbl,
        address=pluto.address if pluto else None,
        borough=bbl_result.borough,
        block=bbl_result.block,
        lot=bbl_result.lot,
        latitude=bbl_result.latitude,
        longitude=bbl_result.longitude,
        pluto=pluto,
        geometry=geometry,
        zoning_districts=zoning_districts,
        overlays=overlays,
        special_districts=special_districts,
        limited_height=pluto.ltdheight if pluto else None,
        split_zone=(pluto.splitzone == "Y") if pluto and pluto.splitzone else False,
        lot_area=pluto.lotarea if pluto else None,
        lot_frontage=pluto.lotfront if pluto else None,
        lot_depth=pluto.lotdepth if pluto else None,
        lot_type=lot_type,
        street_width=street_width,
        is_historic_district=bool(
            pluto and (
                (pluto.histdist and pluto.histdist.strip())
                or (pluto.landmark and pluto.landmark.strip().upper() not in ("", "N"))
            )
        ),
        landmark_name=(
            pluto.landmark.strip()
            if pluto and pluto.landmark and pluto.landmark.strip().upper() not in ("", "N")
            else None
        ),
    )
