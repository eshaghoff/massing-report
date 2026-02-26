#!/usr/bin/env python3
"""
Validate the NYC Zoning Feasibility Engine against real NYC lots.

Runs full analysis on specific test lots and outputs results for manual review.
Can be run against the live API or directly importing the engine.

Usage:
    # Against live API:
    python3 scripts/validate_real_lots.py --api http://localhost:8000

    # Direct import (no server needed):
    cd backend && python3 -m scripts.validate_real_lots
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

# Add backend to path for direct import mode
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "backend")
sys.path.insert(0, BACKEND_DIR)

# ──────────────────────────────────────────────────────────────────
# TEST LOTS
# ──────────────────────────────────────────────────────────────────

TEST_LOTS = [
    {
        "name": "R7A Brooklyn (East New York)",
        "address": "352 Fountain Ave, Brooklyn, NY",
        "verify": [
            "QH program mandatory",
            "Narrow/wide street height limits",
            "MIH if designated area",
            "FAR ~4.6 (R7A)",
        ],
    },
    {
        "name": "R6B Contextual (Park Slope)",
        "address": "555 Union St, Brooklyn, NY",
        "verify": [
            "Low-rise contextual rules",
            "50 ft height limit",
            "FAR 2.0",
            "Street wall requirements",
        ],
    },
    {
        "name": "R7-1 with C2-3 overlay (Queens)",
        "address": "37-28 Junction Blvd, Queens, NY",
        "verify": [
            "Mixed-use scenario present",
            "Commercial overlay FAR",
            "Ground floor retail + residential above",
        ],
    },
    {
        "name": "R6 Wide Street (Brooklyn)",
        "address": "1580 Flatbush Ave, Brooklyn, NY",
        "verify": [
            "Wide street → higher QH FAR (3.0)",
            "Higher height limits than narrow street",
        ],
    },
    {
        "name": "R6 Narrow Street (Brooklyn)",
        "address": "1310 East 95th St, Brooklyn, NY",
        "verify": [
            "Narrow street → QH FAR 2.2",
            "Lower height limits than wide street",
        ],
    },
    {
        "name": "Corner Lot R7+ (Brooklyn)",
        "address": "1 Hanson Pl, Brooklyn, NY",
        "verify": [
            "Corner lot rules applied",
            "Higher lot coverage allowed",
        ],
    },
]


# ──────────────────────────────────────────────────────────────────
# DIRECT ENGINE MODE (no server needed)
# ──────────────────────────────────────────────────────────────────

async def run_direct_analysis(address: str) -> dict:
    """Run analysis by importing the engine directly."""
    from app.services.geocoding import geocode_address
    from app.services.pluto import fetch_pluto_data
    from app.services.geometry import fetch_lot_geometry, fetch_zoning_layers
    from app.services.street_width import determine_street_width
    from app.services.geocoding import BOROUGH_CODE_TO_NAME
    from app.zoning_engine.calculator import ZoningCalculator
    from app.zoning_engine.building_program import generate_building_program
    from app.zoning_engine.parking_layout import evaluate_parking_layouts
    from app.services.report import generate_report
    from app.models.schemas import (
        LotProfile, CalculationResult, SpecialDistrictInfo, BBLResponse,
    )
    from app.config import settings

    # Geocode
    bbl_result = await geocode_address(address)

    # Fetch data
    pluto = await fetch_pluto_data(bbl_result.bbl, settings.socrata_app_token)
    if not pluto:
        return {"error": f"No PLUTO data for BBL {bbl_result.bbl}"}

    geometry = await fetch_lot_geometry(bbl_result.bbl)
    zoning_layers = await fetch_zoning_layers(bbl_result.bbl)

    # Build lot profile
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

    lot_type = "interior"
    if pluto and pluto.irrlotcode and pluto.irrlotcode.strip() == "Y":
        lot_type = "irregular"

    # Street width
    addr = pluto.address if pluto else ""
    borough = bbl_result.borough
    house_number = ""
    street_name = ""
    if addr:
        parts = addr.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].replace("-", "").isdigit():
            house_number = parts[0]
            street_name = parts[1]
    borough_name = BOROUGH_CODE_TO_NAME.get(borough, "")

    street_width = await determine_street_width(
        address=addr, borough=borough,
        house_number=house_number, street_name=street_name,
        borough_name=borough_name,
        latitude=bbl_result.latitude, longitude=bbl_result.longitude,
    )

    lot_profile = LotProfile(
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
    )

    # Calculate
    calculator = ZoningCalculator()
    calc_result = calculator.calculate(lot_profile)

    zoning_envelope = calc_result["zoning_envelope"]
    scenarios = calc_result["scenarios"]

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
            "floors": [{"floor": f.floor, "use": f.use, "gross_sf": f.gross_sf, "net_sf": f.net_sf, "height_ft": f.height_ft} for f in scenario.floors] if scenario.floors else [],
        }
        bp = generate_building_program(
            scenario_dict,
            lot_depth=lot_profile.lot_depth or 100,
            lot_frontage=lot_profile.lot_frontage or 50,
            borough=lot_profile.borough,
        )
        building_programs.append(bp)

    # Parking layout
    parking_layout = None
    pk_scenarios = [s for s in scenarios if s.parking and s.parking.total_spaces_required > 0]
    if pk_scenarios:
        max_pk = max(pk_scenarios, key=lambda s: s.parking.total_spaces_required)
        fp = (lot_profile.lot_area or 5000) * (
            zoning_envelope.lot_coverage_max / 100 if zoning_envelope.lot_coverage_max else 0.65
        )
        parking_layout = evaluate_parking_layouts(
            required_spaces=max_pk.parking.total_spaces_required,
            lot_area=lot_profile.lot_area or 5000,
            building_footprint=fp,
            typical_floor_sf=fp,
            lot_frontage=lot_profile.lot_frontage or 50,
            lot_depth=lot_profile.lot_depth or 100,
            is_quality_housing=zoning_envelope.quality_housing,
            waiver_eligible=max_pk.parking.waiver_eligible,
        )

    # Generate report
    result = CalculationResult(
        lot_profile=lot_profile,
        zoning_envelope=zoning_envelope,
        scenarios=scenarios,
        building_type=calc_result.get("building_type"),
        street_wall=calc_result.get("street_wall"),
        special_districts=SpecialDistrictInfo(**calc_result["special_districts"]) if calc_result.get("special_districts") else None,
        city_of_yes=calc_result.get("city_of_yes"),
    )
    report_path = generate_report(result, parking_layout_result=parking_layout)

    return {
        "lot": lot_profile,
        "envelope": zoning_envelope,
        "scenarios": scenarios,
        "building_programs": building_programs,
        "parking_layout": parking_layout,
        "report_path": report_path,
    }


# ──────────────────────────────────────────────────────────────────
# API MODE
# ──────────────────────────────────────────────────────────────────

async def run_api_analysis(address: str, api_base: str) -> dict:
    """Run analysis via the HTTP API."""
    import httpx
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{api_base}/api/v1/full-analysis",
            json={"address": address},
        )
        if resp.status_code != 200:
            return {"error": f"API returned {resp.status_code}: {resp.text[:500]}"}
        return resp.json()


# ──────────────────────────────────────────────────────────────────
# OUTPUT FORMATTING
# ──────────────────────────────────────────────────────────────────

def format_result(test: dict, result: dict) -> str:
    """Format a single test result for console output."""
    lines = []
    lines.append(f"\n{'='*70}")
    lines.append(f"TEST: {test['name']}")
    lines.append(f"{'='*70}")

    if "error" in result:
        lines.append(f"  ERROR: {result['error']}")
        return "\n".join(lines)

    # Lot info
    lot = result.get("lot")
    if lot:
        if hasattr(lot, "address"):
            # Direct mode — Pydantic models
            lines.append(f"  Address:  {lot.address}")
            lines.append(f"  BBL:      {lot.bbl}")
            lines.append(f"  Zoning:   {', '.join(lot.zoning_districts)}")
            lines.append(f"  Lot:      {lot.lot_area:,.0f} SF, {lot.lot_frontage:.0f}' × {lot.lot_depth:.0f}', {lot.lot_type}")
            lines.append(f"  Street:   {lot.street_width}")
            if lot.overlays:
                lines.append(f"  Overlays: {', '.join(lot.overlays)}")
        else:
            # API mode — dicts
            lines.append(f"  Address:  {lot.get('address', 'N/A')}")
            lines.append(f"  BBL:      {lot.get('bbl', 'N/A')}")
            lines.append(f"  Zoning:   {', '.join(lot.get('zoning_districts', []))}")
            la = lot.get('lot_area', 0)
            lf = lot.get('lot_frontage', 0)
            ld = lot.get('lot_depth', 0)
            lines.append(f"  Lot:      {la:,.0f} SF, {lf:.0f}' × {ld:.0f}', {lot.get('lot_type', 'N/A')}")
            lines.append(f"  Street:   {lot.get('street_width', 'N/A')}")

    # Envelope
    env = result.get("envelope") or result.get("zoning", {}).get("envelope")
    if env:
        if hasattr(env, "residential_far"):
            lines.append(f"\n  ENVELOPE:")
            lines.append(f"    Res FAR:  {env.residential_far}")
            lines.append(f"    QH:       {env.quality_housing}")
            lines.append(f"    Max Ht:   {env.max_building_height} ft")
            lines.append(f"    Lot Cov:  {env.lot_coverage_max}%")
        elif isinstance(env, dict):
            lines.append(f"\n  ENVELOPE:")
            lines.append(f"    Res FAR:  {env.get('residential_far')}")
            lines.append(f"    QH:       {env.get('quality_housing')}")
            lines.append(f"    Max Ht:   {env.get('max_building_height')} ft")
            lines.append(f"    Lot Cov:  {env.get('lot_coverage_max')}%")

    # Scenarios
    scenarios = result.get("scenarios", [])
    building_programs = result.get("building_programs", [])

    if scenarios:
        lines.append(f"\n  SCENARIOS ({len(scenarios)}):")
        for i, s in enumerate(scenarios):
            if hasattr(s, "name"):
                # Pydantic model
                lines.append(f"\n    {s.name}:")
                lines.append(f"      FAR:     {s.far_used:.2f} → ZFA: {s.zoning_floor_area:,.0f} SF")
                lines.append(f"      Height:  {s.max_height_ft:.0f} ft, {s.num_floors} floors")
                lines.append(f"      Units:   {s.total_units}")
                if s.residential_sf:
                    lines.append(f"      Res SF:  {s.residential_sf:,.0f}")
                if s.commercial_sf:
                    lines.append(f"      Comm SF: {s.commercial_sf:,.0f}")
                if s.parking:
                    pk = s.parking
                    lines.append(f"      Parking: {pk.total_spaces_required} required" +
                               (" (waiver eligible)" if pk.waiver_eligible else ""))
            else:
                # Dict (API mode)
                lines.append(f"\n    {s.get('name', 'Scenario')}:")
                lines.append(f"      FAR:     {s.get('far_used', 0):.2f} → ZFA: {s.get('zoning_floor_area', 0):,.0f} SF")
                lines.append(f"      Height:  {s.get('max_height_ft', 0):.0f} ft, {s.get('num_floors', 0)} floors")
                lines.append(f"      Units:   {s.get('total_units', 0)}")

            # Building program
            if i < len(building_programs):
                bp = building_programs[i]
                if hasattr(bp, "loss_factor_pct"):
                    lines.append(f"      Loss:    {bp.loss_factor_pct:.1f}%")
                    if bp.unit_mix_options:
                        best = bp.unit_mix_options[0]
                        mix_str = ", ".join(f"{u['count']} {u['type']}" for u in best.units)
                        lines.append(f"      Mix:     {best.total_units} units ({best.strategy}): {mix_str}")
                elif isinstance(bp, dict):
                    lines.append(f"      Loss:    {bp.get('loss_factor_pct', 'N/A')}%")

    # Parking layout
    pk_layout = result.get("parking_layout")
    if pk_layout:
        if hasattr(pk_layout, "recommended") and pk_layout.recommended:
            rec = pk_layout.recommended
            lines.append(f"\n  PARKING RECOMMENDED: {rec.config_type}")
            lines.append(f"    Spaces: {rec.spaces_provided}, Cost: ${rec.estimated_cost:,.0f}")
        elif isinstance(pk_layout, dict) and pk_layout.get("recommended"):
            rec = pk_layout["recommended"]
            lines.append(f"\n  PARKING RECOMMENDED: {rec.get('config_type', 'N/A')}")

    # Report path
    rp = result.get("report_path", "")
    if rp:
        lines.append(f"\n  PDF saved to: {rp}")

    # Verification checklist
    lines.append(f"\n  VERIFY:")
    for v in test.get("verify", []):
        lines.append(f"    [ ] {v}")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Validate NYC Zoning Engine against real lots")
    parser.add_argument("--api", default=None, help="API base URL (e.g., http://localhost:8000)")
    parser.add_argument("--tests", nargs="*", type=int, help="Run specific test numbers (1-indexed)")
    args = parser.parse_args()

    print(f"\nNYC Zoning Engine Validation")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Mode: {'API' if args.api else 'Direct Import'}")
    if args.api:
        print(f"API:  {args.api}")
    print(f"Tests: {len(TEST_LOTS)} configured")

    # Filter tests if specific ones requested
    tests_to_run = TEST_LOTS
    if args.tests:
        tests_to_run = [TEST_LOTS[i-1] for i in args.tests if 1 <= i <= len(TEST_LOTS)]

    results = []
    for i, test in enumerate(tests_to_run, 1):
        print(f"\n>>> Running test {i}/{len(tests_to_run)}: {test['name']}...")
        try:
            if args.api:
                result = await run_api_analysis(test["address"], args.api)
            else:
                result = await run_direct_analysis(test["address"])
            formatted = format_result(test, result)
            print(formatted)
            results.append({"test": test["name"], "status": "ok"})
        except Exception as e:
            print(f"\n  FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append({"test": test["name"], "status": "error", "error": str(e)})

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    ok = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] == "error")
    print(f"  Passed: {ok}/{len(results)}")
    if err:
        print(f"  Failed: {err}/{len(results)}")
        for r in results:
            if r["status"] == "error":
                print(f"    - {r['test']}: {r.get('error', 'unknown')}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
