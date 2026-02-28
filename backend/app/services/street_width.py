"""
NYC street width detection service.

Determines whether a property fronts on a "wide street" (>=75 ft mapped width)
or a "narrow street" (<75 ft) per the NYC Zoning Resolution.

The mapped street width comes from the City Map and includes the full
right-of-way (curb-to-curb + sidewalks). The ZR definition at ZR 12-10:
  "Wide street" = a street 75 feet or more in width.

Data sources (in priority order):
  1. DCP Digital City Map via Carto SQL API (FREE, no auth required)
     - Table: dcp_dcm_street_centerline on planninglabs.carto.com
     - Uses spatial query (ST_DWithin) to find the nearest street centerline
     - Returns `streetwidt` field = mapped street width in feet
     - This is the SAME data shown on the ZoLa map (zola.planning.nyc.gov)
  2. NYC Geoclient v2 API (requires API key from api-portal.nyc.gov)
     - Returns `streetWidth1a` field = mapped street width in feet
  3. Address-based heuristic (fallback when no APIs are available)

Note: The address heuristic is imperfect. Many numbered streets in Brooklyn
and Queens are wide (>=75 ft) despite not being named "Avenue" or "Boulevard".
The DCP Carto API is free and should always work without configuration.
"""

from __future__ import annotations

import re
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Carto SQL API endpoint for NYC Planning Labs data
CARTO_SQL_URL = "https://planninglabs.carto.com/api/v2/sql"

# ──────────────────────────────────────────────────────────────────
# 1. DCP DIGITAL CITY MAP (PRIMARY — free, no auth)
#    Table: dcp_dcm_street_centerline
#    ZoLa uses this for its street width display.
# ──────────────────────────────────────────────────────────────────


def _parse_street_width(width_str: str) -> float | None:
    """Parse a mapped street width string from DCP Digital City Map.

    The `streetwidt` column uses a variety of formats:
      - Plain number: "80" -> 80.0
      - Greater than: ">80" -> 80.0 (conservative: use the lower bound)
      - Approximately: "~80" -> 80.0
      - Less than: "<80" -> 79.0 (one less, conservative)
      - Range: "80-90" -> 80.0 (use the minimum width)
      - Decimal: "80.5" -> 80.5
      - Combined: ">80.14" -> 80.14

    For zoning purposes we only need to know if >= 75 ft,
    so the conservative approach is safe.
    """
    if not width_str or not width_str.strip():
        return None

    s = width_str.strip()

    # Handle "less than" — be conservative, subtract 1
    if s.startswith("<"):
        s = s[1:]
        try:
            return float(s) - 1.0
        except ValueError:
            return None

    # Strip prefix markers (>, ~)
    s = s.lstrip(">~")

    # Handle ranges like "80-90" — use the minimum
    if "-" in s and not s.startswith("-"):
        parts = s.split("-", 1)
        try:
            return float(parts[0])
        except ValueError:
            return None

    try:
        return float(s)
    except ValueError:
        return None


async def fetch_street_width_from_dcm(
    longitude: float,
    latitude: float,
    search_radius_m: float = 50,
) -> tuple[float | None, str]:
    """Fetch the mapped street width from DCP Digital City Map via Carto SQL API.

    Uses a spatial query to find the nearest street centerline to the
    given coordinates, then returns the `streetwidt` value.

    Args:
        longitude: WGS84 longitude (e.g. -73.928352)
        latitude: WGS84 latitude (e.g. 40.657573)
        search_radius_m: Search radius in meters (default 50m).

    Returns:
        Tuple of (width_in_feet, street_name). Width is None if unavailable.
    """
    # Find the closest street centerline to the property
    sql = (
        "SELECT street_nm, streetwidt, roadwaytyp, feat_statu, "
        "ST_Distance("
        "  the_geom::geography, "
        "  ST_SetSRID(ST_MakePoint({lng},{lat}), 4326)::geography"
        ") AS dist_m "
        "FROM dcp_dcm_street_centerline "
        "WHERE ST_DWithin("
        "  the_geom::geography, "
        "  ST_SetSRID(ST_MakePoint({lng},{lat}), 4326)::geography, "
        "  {radius}"
        ") "
        "ORDER BY dist_m "
        "LIMIT 5"
    ).format(lng=longitude, lat=latitude, radius=search_radius_m)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(CARTO_SQL_URL, params={"q": sql})
            if resp.status_code != 200:
                logger.warning("Carto SQL API returned %d", resp.status_code)
                return None, ""
            data = resp.json()

        rows = data.get("rows", [])
        if not rows:
            # Try a wider search radius
            if search_radius_m < 150:
                return await fetch_street_width_from_dcm(
                    longitude, latitude, search_radius_m=150
                )
            return None, ""

        # The nearest street centerline is the fronting street
        nearest = rows[0]
        street_name = nearest.get("street_nm", "")
        width_str = nearest.get("streetwidt", "")
        width = _parse_street_width(width_str)

        logger.info(
            "DCM street width for (%f, %f): %s = %s ft (parsed: %s)",
            latitude, longitude, street_name, width_str, width,
        )

        return width, street_name
    except Exception as e:
        logger.warning("DCP Carto API error: %s", e)
        return None, ""


async def fetch_street_width_by_name(
    street_name: str,
    borough: int = 0,
) -> float | None:
    """Fetch the mapped street width by street name from the DCP Digital City Map.

    This is a fallback when we don't have coordinates. It searches by name
    and returns the most common width value for that street.

    Args:
        street_name: Street name (e.g. "East 53 Street")
        borough: Borough code (1-5), 0 = all boroughs

    Returns:
        Most common mapped street width in feet, or None.
    """
    # Normalize street name for ILIKE query
    name = street_name.strip().replace("'", "''")

    # Remove ordinal suffixes for matching: "53rd" -> "53"
    name = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', name, flags=re.IGNORECASE)

    sql = (
        "SELECT streetwidt, COUNT(*) as cnt "
        "FROM dcp_dcm_street_centerline "
        "WHERE street_nm ILIKE '%{name}%' "
    ).format(name=name)

    if borough:
        # The DCM table doesn't have a direct borough column,
        # but we can use a spatial filter on the borough boundary
        # For simplicity, we just filter by name — works for unique names
        pass

    sql += "GROUP BY streetwidt ORDER BY cnt DESC LIMIT 1"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(CARTO_SQL_URL, params={"q": sql})
            if resp.status_code != 200:
                return None
            data = resp.json()

        rows = data.get("rows", [])
        if rows:
            return _parse_street_width(rows[0].get("streetwidt", ""))
    except Exception:
        pass

    return None


# ──────────────────────────────────────────────────────────────────
# 2. NYC GEOCLIENT v2 API (requires subscription key)
#    Sign up at: https://api-portal.nyc.gov/signup
# ──────────────────────────────────────────────────────────────────

async def fetch_street_width_from_geoclient(
    house_number: str,
    street_name: str,
    borough: str,
) -> float | None:
    """Fetch the mapped street width from NYC Geoclient v2 API.

    Args:
        house_number: e.g. "110"
        street_name: e.g. "East 53 Street"
        borough: e.g. "Brooklyn" or "3"

    Returns:
        Mapped street width in feet, or None if unavailable.
    """
    key = settings.nyc_geoclient_app_key
    if not key:
        return None

    url = "https://api.nyc.gov/geo/geoclient/v2/address.json"
    params = {
        "houseNumber": house_number,
        "street": street_name,
        "borough": borough,
    }
    headers = {
        "Ocp-Apim-Subscription-Key": key,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                return None
            data = resp.json()

        addr = data.get("address", {})
        # Geoclient returns streetWidth1a (the mapped width of the first street)
        width_str = addr.get("streetWidth1a") or addr.get("streetWidth")
        if width_str:
            return float(width_str)
    except Exception:
        pass

    return None


# ──────────────────────────────────────────────────────────────────
# 3. HEURISTIC FALLBACK (address name-based)
# ──────────────────────────────────────────────────────────────────

# Avenues are almost always >=75 ft mapped width in NYC.
# Boulevards and named wide streets are also typically wide.
WIDE_STREET_KEYWORDS = [
    "AVENUE", "AVE",
    "BOULEVARD", "BLVD",
    "BROADWAY",
    "PARKWAY", "PKWY",
    "CONCOURSE",
    "EXPRESSWAY", "EXPY",
    "TURNPIKE", "TPKE",
    "HIGHWAY", "HWY",
    "PLAZA",
]

# Specific named streets that are wide (>=75 ft) but don't have obvious keywords.
# This is not exhaustive — for accuracy, use the DCP Carto API.
KNOWN_WIDE_STREETS = {
    # Manhattan
    (1, "BOWERY"),
    (1, "PARK ROW"),
    (1, "CANAL STREET"),
    (1, "HOUSTON STREET"),
    (1, "14 STREET"), (1, "14TH STREET"),
    (1, "23 STREET"), (1, "23RD STREET"),
    (1, "34 STREET"), (1, "34TH STREET"),
    (1, "42 STREET"), (1, "42ND STREET"),
    (1, "57 STREET"), (1, "57TH STREET"),
    (1, "72 STREET"), (1, "72ND STREET"),
    (1, "86 STREET"), (1, "86TH STREET"),
    (1, "96 STREET"), (1, "96TH STREET"),
    (1, "110 STREET"), (1, "110TH STREET"),
    (1, "116 STREET"), (1, "116TH STREET"),
    (1, "125 STREET"), (1, "125TH STREET"),
    (1, "135 STREET"), (1, "135TH STREET"),
    (1, "145 STREET"), (1, "145TH STREET"),
    (1, "155 STREET"), (1, "155TH STREET"),
    (1, "DELANCEY STREET"),
    (1, "CHAMBERS STREET"),
    (1, "WORTH STREET"),
    (1, "WEST STREET"),
    (1, "EAST END AVENUE"),  # technically has AVENUE
    # Brooklyn — many "East" numbered streets between Flatbush Ave and
    # Ralph Ave are on the Brooklyn grid with 80 ft mapped widths
    (3, "ATLANTIC AVENUE"),  # has AVENUE
    (3, "EASTERN PARKWAY"),  # has PARKWAY
    (3, "OCEAN PARKWAY"),    # has PARKWAY
    (3, "FLATBUSH AVENUE"),  # has AVENUE
    (3, "4 AVENUE"), (3, "4TH AVENUE"),
    (3, "KINGS HIGHWAY"),    # has HIGHWAY
    # Bronx
    (2, "GRAND CONCOURSE"),  # has CONCOURSE
    (2, "FORDHAM ROAD"),
    (2, "TREMONT AVENUE"),   # has AVENUE
    (2, "BURNSIDE AVENUE"),  # has AVENUE
    # Queens
    (4, "QUEENS BOULEVARD"), # has BOULEVARD
    (4, "NORTHERN BOULEVARD"), # has BOULEVARD
    # Staten Island
    (5, "VICTORY BOULEVARD"), # has BOULEVARD
    (5, "HYLAN BOULEVARD"),   # has BOULEVARD
}


def _normalize_street(street_name: str) -> str:
    """Normalize street name for comparison."""
    s = street_name.upper().strip()
    # Remove ordinal suffixes: 53RD -> 53, 42ND -> 42, etc.
    s = re.sub(r'(\d+)(ST|ND|RD|TH)\b', r'\1', s)
    return s


def is_wide_street_heuristic(address: str, borough: int = 0) -> bool:
    """Determine if an address is on a wide street using name heuristics.

    This is the LAST RESORT fallback. The authoritative source is the
    DCP Digital City Map via Carto SQL API.

    Args:
        address: Full address (e.g. "110 EAST 53 STREET")
        borough: Borough code (1-5)

    Returns:
        True if the street is likely wide (>=75 ft).
    """
    addr_upper = address.upper().strip()

    # Check for wide street keywords
    for keyword in WIDE_STREET_KEYWORDS:
        if keyword in addr_upper:
            return True

    # Extract street name (remove house number)
    parts = addr_upper.split(" ", 1)
    if len(parts) == 2 and parts[0].isdigit():
        street = parts[1]
    else:
        street = addr_upper

    # Check known wide streets
    normalized = _normalize_street(street)
    if borough and (borough, normalized) in KNOWN_WIDE_STREETS:
        return True

    return False


# ──────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────────────────────────

async def determine_street_width(
    address: str,
    borough: int = 0,
    house_number: str = "",
    street_name: str = "",
    borough_name: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
) -> tuple[str, float | None]:
    """Determine street width classification for a property.

    Tries data sources in priority order:
      1. DCP Digital City Map via Carto (spatial query, free, no auth)
      2. Geoclient API (if key configured)
      3. DCP Digital City Map by street name (if no coords)
      4. Address heuristic (last resort)

    Args:
        address: Full address string
        borough: Borough code (1-5)
        house_number: Parsed house number
        street_name: Parsed street name
        borough_name: Borough name for API call
        latitude: WGS84 latitude (if available from geocoding)
        longitude: WGS84 longitude (if available from geocoding)

    Returns:
        Tuple of ("wide" or "narrow", numeric_width_ft or None)
    """
    # ── Source 1: DCP Digital City Map via spatial query (best) ──
    if latitude and longitude:
        width, dcm_street = await fetch_street_width_from_dcm(longitude, latitude)
        if width is not None:
            return ("wide" if width >= 75 else "narrow", width)

    # ── Source 2: Geoclient API (if key configured) ──
    if house_number and street_name and (borough_name or borough):
        boro_str = borough_name or {
            1: "Manhattan", 2: "Bronx", 3: "Brooklyn",
            4: "Queens", 5: "Staten Island",
        }.get(borough, "")

        width = await fetch_street_width_from_geoclient(
            house_number, street_name, boro_str
        )
        if width is not None:
            return ("wide" if width >= 75 else "narrow", width)

    # ── Source 3: DCP Digital City Map by street name (fallback) ──
    if street_name:
        width = await fetch_street_width_by_name(street_name, borough)
        if width is not None:
            return ("wide" if width >= 75 else "narrow", width)

    # ── Source 4: Address heuristic (last resort) ──
    classification = "wide" if is_wide_street_heuristic(address, borough) else "narrow"
    # Estimate numeric width from classification when no data available
    fallback_ft = 80.0 if classification == "wide" else 60.0
    return (classification, fallback_ft)
