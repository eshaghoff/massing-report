from __future__ import annotations

import httpx


async def fetch_lot_geometry(bbl: str) -> dict | None:
    """Fetch lot polygon geometry from Carto (MapPLUTO) as GeoJSON.

    Tries multiple MapPLUTO version table names since they change with releases.
    """
    table_names = [
        "dcp_mappluto",
        "mappluto_25v1",
        "mappluto_24v4",
        "mappluto_24v3",
        "mappluto_24v2",
        "mappluto_24v1",
        "mappluto_23v3",
    ]

    for table in table_names:
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
    url = "https://planninglabs.carto.com/api/v2/sql"
    params = {"q": query}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()

        rows = data.get("rows", [])
        if not rows:
            return None

        import json
        geom_str = rows[0].get("geom")
        if not geom_str:
            return None

        return json.loads(geom_str)
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
