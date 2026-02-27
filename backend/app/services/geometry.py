from __future__ import annotations

import json
import logging
from collections import Counter
from statistics import median, mode

import httpx

logger = logging.getLogger(__name__)


# MapPLUTO table versions to try (newest first)
_TABLE_NAMES = [
    "dcp_mappluto",
    "mappluto_25v1",
    "mappluto_24v4",
    "mappluto_24v3",
    "mappluto_24v2",
    "mappluto_24v1",
    "mappluto_23v3",
]

_CARTO_URL = "https://planninglabs.carto.com/api/v2/sql"


async def fetch_lot_geometry(bbl: str) -> dict | None:
    """Fetch lot polygon geometry from Carto (MapPLUTO) as GeoJSON.

    Tries multiple MapPLUTO version table names since they change with releases.
    """
    for table in _TABLE_NAMES:
        result = await _query_carto(bbl, table)
        if result:
            return result
    return None


async def _query_carto(bbl: str, table_name: str) -> dict | None:
    """Query Carto SQL API for lot geometry."""
    query = (
        f"SELECT ST_AsGeoJSON(the_geom) as geom, bbl, lotarea, lotfront, lotdepth "
        f"FROM {table_name} WHERE bbl = '{bbl}'"
    )
    params = {"q": query}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(_CARTO_URL, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()

        rows = data.get("rows", [])
        if not rows:
            return None

        geom_str = rows[0].get("geom")
        if not geom_str:
            return None

        return json.loads(geom_str)
    except Exception:
        return None


async def fetch_adjacent_lots(
    bbl: str,
    min_boundary_ft: float = 10.0,
) -> list[dict]:
    """Find lots sharing >= min_boundary_ft of boundary with the given BBL.

    Per NYC ZR Section 12-10, a zoning lot merger requires lots to be
    contiguous for a minimum of 10 linear feet on the same block.

    Uses Carto MapPLUTO spatial queries with ST_Transform to EPSG:2263
    (NY State Plane, units in feet) for accurate boundary measurement.
    """
    for table in _TABLE_NAMES:
        result = await _query_adjacent(bbl, table, min_boundary_ft)
        if result is not None:
            return result
    return []


async def _query_adjacent(
    bbl: str,
    table_name: str,
    min_boundary_ft: float,
) -> list[dict] | None:
    """Run spatial adjacent-lots query against a specific MapPLUTO table."""
    # ST_Transform to EPSG:2263 (NY State Plane Long Island, feet)
    # ST_Boundary extracts the ring/edge of each polygon
    # ST_Intersection of the two boundaries gives the shared edge(s)
    # ST_Length measures that shared edge in feet
    query = f"""
    SELECT * FROM (
        SELECT
            b.bbl,
            b.address,
            b.lotarea,
            b.lotfront,
            b.lotdepth,
            b.bldgarea,
            b.builtfar,
            b.numfloors,
            b.yearbuilt,
            b.zonedist1,
            b.zonedist2,
            ST_AsGeoJSON(b.the_geom) as geom,
            ST_Length(
                ST_Intersection(
                    ST_Boundary(ST_Transform(a.the_geom, 2263)),
                    ST_Boundary(ST_Transform(b.the_geom, 2263))
                )
            ) as shared_boundary_ft
        FROM {table_name} a
        JOIN {table_name} b
            ON a.bbl != b.bbl
            AND a.block = b.block
            AND ST_Intersects(
                ST_Buffer(a.the_geom, 0.00001),
                b.the_geom
            )
        WHERE a.bbl = '{bbl}'
    ) sub
    WHERE shared_boundary_ft >= {min_boundary_ft}
    ORDER BY shared_boundary_ft DESC
    """

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(_CARTO_URL, params={"q": query})
            if resp.status_code != 200:
                return None
            data = resp.json()

        rows = data.get("rows", [])
        results = []
        for row in rows:
            geom_str = row.get("geom")
            geometry = json.loads(geom_str) if geom_str else None
            results.append({
                "bbl": str(row.get("bbl", "")),
                "address": row.get("address", ""),
                "lot_area": row.get("lotarea") or 0,
                "lot_frontage": row.get("lotfront") or 0,
                "lot_depth": row.get("lotdepth") or 0,
                "bldgarea": row.get("bldgarea") or 0,
                "builtfar": row.get("builtfar") or 0,
                "numfloors": row.get("numfloors") or 0,
                "yearbuilt": row.get("yearbuilt") or 0,
                "zoning_districts": [
                    d for d in [row.get("zonedist1"), row.get("zonedist2")]
                    if d
                ],
                
                "shared_boundary_ft": round(row.get("shared_boundary_ft", 0), 1),
                "geometry": geometry,
            })
        return results
    except Exception:
        return None


async def fetch_zoning_layers(bbl: str) -> dict:
    """Fetch additional zoning layers from NYC Zoning API."""
    url = f"https://zoning.planningdigital.com/api/tax-lots?bbl={bbl}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {}
            return resp.json()
    except Exception:
        return {}



# ──────────────────────────────────────────────────────────────────
# BLOCK CHARACTER DESCRIPTION
# ──────────────────────────────────────────────────────────────────

# Land use code -> human-readable description
_LAND_USE_DESCRIPTIONS = {
    "01": "one- and two-family residential",
    "02": "multi-family walk-up residential",
    "03": "multi-family elevator residential",
    "04": "mixed residential and commercial",
    "05": "commercial and office",
    "06": "industrial and manufacturing",
    "07": "transportation and utility",
    "08": "public facilities and institutions",
    "09": "open space and outdoor recreation",
    "10": "parking facilities",
    "11": "vacant land",
}


async def fetch_block_description(bbl: str) -> str | None:
    """Generate a natural-language description of the block character.

    Queries PLUTO for all lots on the same block (same borough + block number),
    aggregates key statistics (building heights, land use, year built, FAR),
    and returns a 1-2 sentence description like:

        "The block consists mostly of 6-story multifamily walk-up buildings
        (median year built 1927). Average built FAR is 3.45."

    Returns None if data is unavailable.
    """
    if not bbl or len(bbl) < 6:
        return None

    # Extract borough code and block number from BBL
    boro = bbl[0]
    block = bbl[1:6].lstrip("0") or "0"

    for table in _TABLE_NAMES:
        result = await _query_block_data(boro, block, table)
        if result is not None:
            return _format_block_description(result)
    return None


async def _query_block_data(boro: str, block: str, table_name: str) -> list[dict] | None:
    """Query PLUTO for all lots on a given block."""
    query = (
        f"SELECT numfloors, landuse, bldgarea, lotarea, builtfar, yearbuilt "
        f"FROM {table_name} "
        f"WHERE borocode = '{boro}' AND block = '{block}' "
        f"LIMIT 150"
    )
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(_CARTO_URL, params={"q": query})
            if resp.status_code != 200:
                return None
            data = resp.json()
        rows = data.get("rows", [])
        if not rows:
            return None
        return rows
    except Exception as e:
        logger.warning("Block data query failed for block %s: %s", block, e)
        return None


def _format_block_description(rows: list[dict]) -> str:
    """Format block PLUTO data into natural language description."""
    # Collect valid values
    floors_list = [r["numfloors"] for r in rows if r.get("numfloors") and r["numfloors"] > 0]
    landuse_list = [str(r["landuse"]).zfill(2) for r in rows if r.get("landuse")]
    year_list = [r["yearbuilt"] for r in rows if r.get("yearbuilt") and r["yearbuilt"] > 1800]
    far_list = [r["builtfar"] for r in rows if r.get("builtfar") and r["builtfar"] > 0]

    if not floors_list and not landuse_list:
        return None

    parts = []

    # Dominant land use
    dominant_use = ""
    if landuse_list:
        use_counts = Counter(landuse_list)
        most_common_code = use_counts.most_common(1)[0][0]
        dominant_use = _LAND_USE_DESCRIPTIONS.get(most_common_code, "")

    # Median floors
    median_floors = 0
    if floors_list:
        median_floors = round(median(floors_list))

    # Build first sentence
    if median_floors > 0 and dominant_use:
        parts.append(
            f"The block consists mostly of {median_floors}-story "
            f"{dominant_use} buildings"
        )
    elif median_floors > 0:
        parts.append(f"The block consists mostly of {median_floors}-story buildings")
    elif dominant_use:
        parts.append(f"The block consists mostly of {dominant_use} buildings")

    # Median year built
    if year_list:
        median_year = round(median(year_list))
        if parts:
            parts[-1] += f" (median year built {median_year})"
        else:
            parts.append(f"Median year built on the block is {median_year}")

    # Add period to first sentence
    if parts:
        parts[-1] += "."

    # Average built FAR
    if far_list:
        avg_far = sum(far_list) / len(far_list)
        parts.append(f"Average built FAR is {avg_far:.2f}.")

    # Total lots context
    if len(rows) > 3:
        parts.append(f"The block contains {len(rows)} tax lots.")

    return " ".join(parts) if parts else None
