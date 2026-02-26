"""
Redis caching layer for NYC Zoning Engine.

TTLs:
  - PLUTO data by BBL: 24 hours
  - Geocoding results by normalized address: 24 hours
  - Street width results by coordinates: 7 days
  - Full analysis results by BBL: 1 hour
"""

from __future__ import annotations

import json
import hashlib
from typing import Optional

import redis.asyncio as redis

from app.config import settings

_redis_client: Optional[redis.Redis] = None

# TTLs in seconds
TTL_PLUTO = 86400       # 24 hours
TTL_GEOCODE = 86400     # 24 hours
TTL_STREET_WIDTH = 604800  # 7 days
TTL_ANALYSIS = 3600     # 1 hour


async def get_redis() -> Optional[redis.Redis]:
    """Get or create Redis client. Returns None if Redis is not configured."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = settings.redis_url
    if not redis_url:
        return None

    try:
        _redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        await _redis_client.ping()
        return _redis_client
    except Exception:
        _redis_client = None
        return None


def _make_key(prefix: str, identifier: str) -> str:
    """Build a cache key."""
    return f"nyc_zoning:{prefix}:{identifier}"


def _normalize_address(address: str) -> str:
    """Normalize an address for cache keying."""
    return hashlib.md5(address.lower().strip().encode()).hexdigest()


async def cache_get(prefix: str, identifier: str) -> Optional[dict]:
    """Get a cached value. Returns None on miss or Redis unavailable."""
    r = await get_redis()
    if not r:
        return None
    try:
        key = _make_key(prefix, identifier)
        val = await r.get(key)
        if val:
            return json.loads(val)
    except Exception:
        pass
    return None


async def cache_set(prefix: str, identifier: str, data: dict, ttl: int = TTL_ANALYSIS) -> bool:
    """Set a cached value. Returns True on success."""
    r = await get_redis()
    if not r:
        return False
    try:
        key = _make_key(prefix, identifier)
        await r.setex(key, ttl, json.dumps(data, default=str))
        return True
    except Exception:
        return False


async def cache_delete(prefix: str, identifier: str) -> bool:
    """Delete a cached value."""
    r = await get_redis()
    if not r:
        return False
    try:
        key = _make_key(prefix, identifier)
        await r.delete(key)
        return True
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTIONS
# ──────────────────────────────────────────────────────────────────

async def get_cached_pluto(bbl: str) -> Optional[dict]:
    return await cache_get("pluto", bbl)


async def set_cached_pluto(bbl: str, data: dict):
    await cache_set("pluto", bbl, data, TTL_PLUTO)


async def get_cached_geocode(address: str) -> Optional[dict]:
    return await cache_get("geocode", _normalize_address(address))


async def set_cached_geocode(address: str, data: dict):
    await cache_set("geocode", _normalize_address(address), data, TTL_GEOCODE)


async def get_cached_street_width(lat: float, lng: float) -> Optional[str]:
    key = f"{lat:.6f},{lng:.6f}"
    result = await cache_get("street_width", key)
    if result:
        return result.get("width")
    return None


async def set_cached_street_width(lat: float, lng: float, width: str):
    key = f"{lat:.6f},{lng:.6f}"
    await cache_set("street_width", key, {"width": width}, TTL_STREET_WIDTH)


async def get_cached_analysis(bbl: str) -> Optional[dict]:
    return await cache_get("analysis", bbl)


async def set_cached_analysis(bbl: str, data: dict):
    await cache_set("analysis", bbl, data, TTL_ANALYSIS)
