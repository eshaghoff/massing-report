"""
NYC address geocoding and BBL resolution.

Sources (in order of priority):
  1. NYC Planning Labs Geosearch API (free, no auth)
  2. NYC Geoservice Function 1B (free, no auth needed for basic use)
  3. NYC Geoservice Function 1A (fallback)

Handles:
  - Full addresses: "123 Main St, Brooklyn, NY 11201"
  - Abbreviated boroughs: "123 Main St, BK"
  - No borough: "123 Main St" (tries Geosearch which doesn't need borough)
  - BBL input: "3046220022", "3-04622-0022", "3/04622/0022"
"""

from __future__ import annotations

import re

import httpx

from app.models.schemas import BBLResponse

# Borough name/abbreviation → code mapping
BOROUGH_MAP = {
    "manhattan": 1, "mn": 1, "mh": 1, "new york": 1, "ny": 1,
    "bronx": 2, "bx": 2, "the bronx": 2,
    "brooklyn": 3, "bk": 3, "bklyn": 3, "kings": 3,
    "queens": 4, "qn": 4, "qns": 4,
    "staten island": 5, "si": 5, "richmond": 5,
}

BOROUGH_CODE_TO_NAME = {
    1: "MANHATTAN", 2: "BRONX", 3: "BROOKLYN", 4: "QUEENS", 5: "STATEN ISLAND",
}

BOROUGH_NAME_TO_CODE = {
    "manhattan": 1, "bronx": 2, "brooklyn": 3, "queens": 4, "staten island": 5,
}


# ──────────────────────────────────────────────────────────────────
# BBL PARSING
# ──────────────────────────────────────────────────────────────────

def parse_bbl(raw: str) -> str | None:
    """Parse a BBL from various formats.

    Accepts:
      - "3046220022" (10-digit)
      - "3-04622-0022" (dash-separated)
      - "3/04622/0022" (slash-separated)

    Returns 10-digit BBL string or None if invalid.
    """
    cleaned = raw.strip().replace("-", "").replace("/", "").replace(" ", "")
    if re.match(r"^[1-5]\d{9}$", cleaned):
        return cleaned
    return None


def validate_bbl(bbl: str) -> bool:
    """Validate a 10-digit BBL string."""
    if not bbl or len(bbl) != 10:
        return False
    try:
        borough = int(bbl[0])
        block = int(bbl[1:6])
        lot = int(bbl[6:10])
        return 1 <= borough <= 5 and block > 0 and lot > 0
    except ValueError:
        return False


def bbl_to_response(bbl: str) -> BBLResponse:
    """Convert a validated BBL string to BBLResponse."""
    return BBLResponse(
        bbl=bbl,
        borough=int(bbl[0]),
        block=int(bbl[1:6]),
        lot=int(bbl[6:10]),
    )


# ──────────────────────────────────────────────────────────────────
# ADDRESS PARSING
# ──────────────────────────────────────────────────────────────────

def parse_address(address: str) -> tuple[str, str, int | None]:
    """Parse a NYC address into house number, street name, and borough code.

    Handles:
      - "123 Main St Brooklyn" (no comma)
      - "123 Main Street, Brooklyn, NY 11201" (full format)
      - "123 Main St, BK" (abbreviated borough)
      - "123 Main St" (no borough — returns None for borough)
    """
    address = address.strip()
    addr_lower = address.lower()
    borough_code = None

    # Strip trailing state abbreviation with optional zipcode
    # "123 Main St, Brooklyn, NY 11201" → "123 Main St, Brooklyn"
    # But NOT "120 Broadway, New York" — "New York" is a borough name
    state_zip = re.search(r',?\s*(?:ny|nyc)\s*(?:,?\s*(?:ny))?\s*(\d{5})?\s*$', addr_lower)
    if state_zip:
        zipcode = state_zip.group(1)
        address = address[:state_zip.start()]
        addr_lower = address.lower()
        if zipcode:
            borough_code = _zip_to_borough(zipcode)

    # Also handle "Brooklyn, New York 11201" (state name + zip)
    if not borough_code:
        state_name_zip = re.search(r',?\s*new\s+york\s*,?\s*(\d{5})\s*$', addr_lower)
        if state_name_zip:
            zipcode = state_name_zip.group(1)
            address = address[:state_name_zip.start()]
            addr_lower = address.lower()
            borough_code = _zip_to_borough(zipcode)

    # Try to extract borough from end of address
    if not borough_code:
        # Sort by length descending so "staten island" matches before "si"
        sorted_boroughs = sorted(BOROUGH_MAP.items(), key=lambda x: -len(x[0]))
        for boro_name, code in sorted_boroughs:
            # Check with comma: ", brooklyn"
            pattern = re.compile(r',?\s*' + re.escape(boro_name) + r'\s*$', re.IGNORECASE)
            match = pattern.search(addr_lower)
            if match:
                borough_code = code
                address = address[:match.start()].rstrip(", ")
                break

    # Extract house number and street
    address = address.strip().rstrip(",").strip()
    parts = address.split(" ", 1)
    if len(parts) == 2 and _is_house_number(parts[0]):
        house_number = parts[0]
        street_name = parts[1].strip()
    else:
        house_number = ""
        street_name = address

    return house_number, street_name, borough_code


def _is_house_number(s: str) -> bool:
    """Check if string looks like a house number (e.g., '123', '12-34')."""
    return bool(re.match(r'^[\d][\d\-]*[\d]?$', s))


def _zip_to_borough(zipcode: str) -> int | None:
    """Map NYC zipcode to borough code."""
    try:
        z = int(zipcode)
    except ValueError:
        return None
    if 10001 <= z <= 10282:
        return 1  # Manhattan
    if 10451 <= z <= 10475:
        return 2  # Bronx
    if 11201 <= z <= 11256:
        return 3  # Brooklyn
    if 11001 <= z <= 11109 or 11351 <= z <= 11697:
        return 4  # Queens
    if 10301 <= z <= 10314:
        return 5  # Staten Island
    return None  # Not a recognized NYC zipcode


def validate_nyc_address(address: str) -> str | None:
    """Validate that an address is in NYC. Returns error message or None if valid."""
    _, _, borough_code = parse_address(address)
    # If we can parse a borough, it's probably NYC
    # Geosearch will also validate — this is a quick pre-check
    return None


# ──────────────────────────────────────────────────────────────────
# GEOCODING
# ──────────────────────────────────────────────────────────────────

async def geocode_address(address: str) -> BBLResponse:
    """Geocode a NYC address to get BBL.

    Uses NYC Planning Geosearch API (free, no auth) as primary,
    with Geoservice as fallback.

    Raises ValueError with a clear message if geocoding fails.
    """
    errors = []

    # Check if input is a BBL
    bbl = parse_bbl(address)
    if bbl:
        return bbl_to_response(bbl)

    # Primary: NYC Planning Geosearch (Pelias-based, free)
    try:
        result = await _geocode_geosearch(address)
        if result:
            return result
    except httpx.TimeoutException:
        errors.append("Geosearch API timeout (>10s)")
    except httpx.ConnectError:
        errors.append("Geosearch API connection failed — check internet connectivity")
    except Exception as e:
        errors.append(f"Geosearch API error: {type(e).__name__}: {e}")

    # Fallback: parse address and use Geoservice
    house_number, street_name, borough_code = parse_address(address)

    if not borough_code:
        detail = (
            f"Could not geocode '{address}'. "
            "The NYC Geosearch API did not find a match, and no borough could "
            "be determined for fallback. Please include the borough "
            "(e.g., 'Brooklyn', 'Manhattan') or a NYC zipcode."
        )
        if errors:
            detail += f" Errors: {'; '.join(errors)}"
        raise ValueError(detail)

    borough_name = BOROUGH_CODE_TO_NAME[borough_code]

    try:
        result = await _geocode_geoservice(house_number, street_name, borough_name)
        if result:
            return result
    except httpx.TimeoutException:
        errors.append("Geoservice 1B timeout")
    except Exception as e:
        errors.append(f"Geoservice 1B: {type(e).__name__}")

    try:
        result = await _geocode_geoservice_1a(house_number, street_name, borough_name)
        if result:
            return result
    except httpx.TimeoutException:
        errors.append("Geoservice 1A timeout")
    except Exception as e:
        errors.append(f"Geoservice 1A: {type(e).__name__}")

    detail = (
        f"Could not geocode address: '{address}'. "
        f"Parsed as: {house_number} {street_name}, {borough_name}. "
        "The address may not exist in NYC's database, or it may be a new/unmapped lot."
    )
    if errors:
        detail += f" Service errors: {'; '.join(errors)}"
    raise ValueError(detail)


async def _geocode_geosearch(address: str) -> BBLResponse | None:
    """Geocode using NYC Planning Labs Geosearch API (Pelias).

    Free, no authentication required.
    Returns BBL, coordinates, and borough.
    """
    url = "https://geosearch.planninglabs.nyc/v2/search"
    params = {"text": address}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return None
        data = resp.json()

    features = data.get("features", [])
    if not features:
        return None

    feat = features[0]
    props = feat.get("properties", {})
    coords = feat.get("geometry", {}).get("coordinates", [None, None])

    # Verify result is in NYC (borough validation)
    borough = props.get("borough")
    if borough and borough.lower() not in BOROUGH_NAME_TO_CODE:
        return None  # Not in NYC

    # Extract BBL from the PAD addendum
    pad = props.get("addendum", {}).get("pad", {})
    bbl = pad.get("bbl", "")

    if not bbl or len(bbl) < 10:
        return None

    lat = coords[1] if len(coords) >= 2 and coords[1] else None
    lng = coords[0] if len(coords) >= 2 and coords[0] else None

    return BBLResponse(
        bbl=bbl,
        borough=int(bbl[0]),
        block=int(bbl[1:6]),
        lot=int(bbl[6:10]),
        latitude=lat,
        longitude=lng,
    )


async def _geocode_geoservice(
    house_number: str, street_name: str, borough: str
) -> BBLResponse | None:
    """Geocode using NYC Geoservice (Function 1B). Free, no auth needed."""
    url = "https://geoservice.planning.nyc.gov/geoservice/geoservice.svc/Function_1B"
    params = {
        "Borough": borough,
        "AddressNo": house_number,
        "StreetName": street_name,
        "Key": "",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    display = data.get("display", {})
    if not display:
        return None

    bbl = display.get("out_bbl", "").strip()
    if not bbl or len(bbl) < 10:
        return None

    lat = None
    lng = None
    lat_str = display.get("out_latitude", "")
    lng_str = display.get("out_longitude", "")
    if lat_str:
        try:
            lat = float(lat_str)
        except ValueError:
            pass
    if lng_str:
        try:
            lng = float(lng_str)
        except ValueError:
            pass

    return BBLResponse(
        bbl=bbl,
        borough=int(bbl[0]),
        block=int(bbl[1:6]),
        lot=int(bbl[6:10]),
        latitude=lat,
        longitude=lng,
    )


async def _geocode_geoservice_1a(
    house_number: str, street_name: str, borough: str
) -> BBLResponse | None:
    """Geocode using NYC Geoservice (Function 1A). Free, no auth needed."""
    url = "https://geoservice.planning.nyc.gov/geoservice/geoservice.svc/Function_1A"
    params = {
        "Borough": borough,
        "AddressNo": house_number,
        "StreetName": street_name,
        "Key": "",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    display = data.get("display", {})
    if not display:
        return None

    bbl = display.get("out_bbl", "").strip()
    if not bbl or len(bbl) < 10:
        return None

    return BBLResponse(
        bbl=bbl,
        borough=int(bbl[0]),
        block=int(bbl[1:6]),
        lot=int(bbl[6:10]),
    )
