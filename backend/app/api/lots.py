"""
Lot Lookup & Adjacent Lots API.

Provides endpoints for:
  - Looking up a single lot by address or BBL
  - Finding qualifying adjacent lots for assemblage (≥10ft shared boundary)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.geocoding import geocode_address, BOROUGH_CODE_TO_NAME
from app.services.pluto import fetch_pluto_data
from app.services.geometry import fetch_lot_geometry, fetch_zoning_layers, fetch_adjacent_lots
from app.services.street_width import determine_street_width
from app.config import settings
from app.models.schemas import LotProfile


router = APIRouter(prefix="/api/v1/saas/lots", tags=["lots"])


# ──────────────────────────────────────────────────────────────────
# SHARED LOT BUILDER (mirrors routes.py _build_lot_profile)
# ──────────────────────────────────────────────────────────────────

async def resolve_lot(
    address: str | None = None,
    bbl: str | None = None,
) -> tuple[LotProfile, dict | None]:
    """Full lot resolution: geocode → PLUTO → geometry → LotProfile.

    Returns (lot_profile, geometry_geojson).
    """
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
        raise HTTPException(
            status_code=404, detail=f"No PLUTO data for BBL {resolved_bbl}"
        )

    # Fetch geometry + zoning layers
    geometry = None
    try:
        geometry = await fetch_lot_geometry(resolved_bbl)
    except Exception:
        pass

    zoning_layers = None
    try:
        zoning_layers = await fetch_zoning_layers(resolved_bbl)
    except Exception:
        pass

    # Build LotProfile (same logic as routes.py _build_lot_profile)
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

    # Determine street width
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
        address=addr,
        borough=borough,
        house_number=house_number,
        street_name=street_name,
        borough_name=borough_name,
        latitude=getattr(bbl_result, "latitude", None),
        longitude=getattr(bbl_result, "longitude", None),
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

    return lot_profile, geometry


# ──────────────────────────────────────────────────────────────────
# ENDPOINTS
# ──────────────────────────────────────────────────────────────────

@router.get("/lookup")
async def lookup_lot(
    address: str | None = Query(None),
    bbl: str | None = Query(None),
):
    """Look up a single lot and return card-level data for the UI.

    Accepts either an address or BBL. Returns lot dimensions, zoning,
    existing building info, and geometry for map preview.
    """
    lot, geometry = await resolve_lot(address=address, bbl=bbl)

    return {
        "bbl": lot.bbl,
        "address": lot.address,
        "borough": lot.borough,
        "block": lot.block,
        "lot": lot.lot,
        "latitude": lot.latitude,
        "longitude": lot.longitude,
        "lot_area": lot.lot_area,
        "lot_frontage": lot.lot_frontage,
        "lot_depth": lot.lot_depth,
        "lot_type": lot.lot_type,
        "street_width": lot.street_width,
        "zoning_districts": lot.zoning_districts,
        "overlays": lot.overlays,
        "special_districts": lot.special_districts,
        "bldgarea": (lot.pluto.bldgarea if lot.pluto else None) or 0,
        "builtfar": (lot.pluto.builtfar if lot.pluto else None) or 0,
        "numfloors": (lot.pluto.numfloors if lot.pluto else None) or 0,
        "yearbuilt": (lot.pluto.yearbuilt if lot.pluto else None) or 0,
        # units_res not in PlutoData schema
        "geometry": geometry,
    }


@router.get("/adjacent/{bbl}")
async def get_adjacent_lots(bbl: str):
    """Find lots qualifying for zoning lot merger with the given BBL.

    Per NYC ZR Section 12-10, qualifying lots must:
      - Be on the same block
      - Share a common boundary of at least 10 linear feet

    Returns a list of adjacent lots with their shared boundary length,
    lot dimensions, existing building info, and zoning.
    """
    # Validate BBL format
    clean_bbl = bbl.replace("-", "").replace("/", "")
    if len(clean_bbl) != 10 or not clean_bbl.isdigit():
        raise HTTPException(status_code=400, detail=f"Invalid BBL format: {bbl}")

    adjacent = await fetch_adjacent_lots(clean_bbl, min_boundary_ft=10.0)

    if adjacent is None:
        raise HTTPException(
            status_code=502,
            detail="Could not query adjacent lots. Geometry data may be unavailable.",
        )

    return {
        "source_bbl": clean_bbl,
        "adjacent_lots": adjacent,
        "count": len(adjacent),
        "min_boundary_ft": 10.0,
    }
