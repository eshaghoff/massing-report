from __future__ import annotations

import json
import httpx


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
