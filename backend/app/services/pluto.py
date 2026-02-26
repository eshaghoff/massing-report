from __future__ import annotations

import httpx

from app.models.schemas import PlutoData

PLUTO_SOCRATA_URL = "https://data.cityofnewyork.us/resource/64uk-42ks.json"

PLUTO_FIELDS = [
    "bbl", "address", "zonedist1", "zonedist2", "zonedist3", "zonedist4",
    "overlay1", "overlay2", "spdist1", "spdist2", "spdist3",
    "ltdheight", "splitzone", "landuse", "lotarea", "lotfront", "lotdepth",
    "bldgarea", "numbldgs", "numfloors", "assessland", "assesstot",
    "builtfar", "residfar", "commfar", "facilfar",
    "yearbuilt", "yearalter1", "yearalter2",
    "irrlotcode", "ext", "cd", "ct2010", "cb2010", "zipcode",
]


async def fetch_pluto_data(bbl: str, app_token: str = "") -> PlutoData | None:
    """Fetch PLUTO data for a given BBL from NYC Open Data Socrata API."""
    params = {"bbl": bbl}
    headers = {}
    if app_token:
        headers["X-App-Token"] = app_token

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(PLUTO_SOCRATA_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    if not data:
        return None

    record = data[0]
    return _parse_pluto_record(record)


def _parse_pluto_record(record: dict) -> PlutoData:
    """Parse a raw PLUTO Socrata record into our schema."""
    def _float(val):
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _int(val):
        if val is None:
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    return PlutoData(
        bbl=str(record.get("bbl", "")),
        address=record.get("address"),
        zonedist1=record.get("zonedist1"),
        zonedist2=record.get("zonedist2"),
        zonedist3=record.get("zonedist3"),
        zonedist4=record.get("zonedist4"),
        overlay1=record.get("overlay1"),
        overlay2=record.get("overlay2"),
        spdist1=record.get("spdist1"),
        spdist2=record.get("spdist2"),
        spdist3=record.get("spdist3"),
        ltdheight=str(record.get("ltdheight", "")) if record.get("ltdheight") is not None else None,
        splitzone=str(record.get("splitzone", "")) if record.get("splitzone") is not None else None,
        landuse=record.get("landuse"),
        lotarea=_float(record.get("lotarea")),
        lotfront=_float(record.get("lotfront")),
        lotdepth=_float(record.get("lotdepth")),
        bldgarea=_float(record.get("bldgarea")),
        numbldgs=_int(record.get("numbldgs")),
        numfloors=_float(record.get("numfloors")),
        assessland=_float(record.get("assessland")),
        assesstot=_float(record.get("assesstot")),
        builtfar=_float(record.get("builtfar")),
        residfar=_float(record.get("residfar")),
        commfar=_float(record.get("commfar")),
        facilfar=_float(record.get("facilfar")),
        yearbuilt=_int(record.get("yearbuilt")),
        yearalter1=_int(record.get("yearalter1")),
        yearalter2=_int(record.get("yearalter2")),
        irrlotcode=str(record.get("irrlotcode", "")) if record.get("irrlotcode") is not None else None,
        ext=record.get("ext"),
        cd=_int(record.get("cd")),
        ct2010=record.get("ct2010"),
        cb2010=record.get("cb2010"),
        zipcode=record.get("zipcode"),
    )
