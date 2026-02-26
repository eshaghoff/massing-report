"""Clerk JWT authentication for FastAPI.

Verifies Bearer tokens against Clerk JWKS endpoint.
Provides get_current_user dependency for protected routes.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

import jwt
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

security = HTTPBearer(auto_error=False)

# Dev mode: skip JWT verification when CLERK_DOMAIN is not set
_DEV_MODE = not settings.clerk_domain

# In-memory JWKS cache
_jwks_cache: dict = {"keys": [], "fetched_at": 0}
_JWKS_TTL = 3600  # 1 hour


@dataclass
class UserInfo:
    """Authenticated user info from Clerk JWT."""
    clerk_user_id: str
    email: str
    first_name: str = ""
    last_name: str = ""


async def _get_jwks() -> list[dict]:
    """Fetch and cache Clerk JWKS keys."""
    now = time.time()
    if _jwks_cache["keys"] and (now - _jwks_cache["fetched_at"]) < _JWKS_TTL:
        return _jwks_cache["keys"]

    domain = settings.clerk_domain
    if not domain:
        raise HTTPException(500, "CLERK_DOMAIN not configured")

    url = f"https://{domain}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

    _jwks_cache["keys"] = data.get("keys", [])
    _jwks_cache["fetched_at"] = now
    return _jwks_cache["keys"]


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> UserInfo:
    """FastAPI dependency: verify Clerk JWT and return user info.

    Returns UserInfo with: clerk_user_id, email, first_name, last_name.
    Raises 401 if token is missing/invalid.
    """
    # Dev mode: return a test user when Clerk is not configured
    if _DEV_MODE:
        return UserInfo(
            clerk_user_id="dev_user_001",
            email="dev@localhost",
            first_name="Dev",
            last_name="User",
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    token = credentials.credentials

    try:
        jwks = await _get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        key_data = None
        for k in jwks:
            if k.get("kid") == kid:
                key_data = k
                break

        if not key_data:
            raise HTTPException(401, "Token signing key not found")

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=f"https://{settings.clerk_domain}",
            options={"verify_aud": False},
        )

        return UserInfo(
            clerk_user_id=payload.get("sub", ""),
            email=payload.get("email", ""),
            first_name=payload.get("first_name", ""),
            last_name=payload.get("last_name", ""),
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, f"Invalid token: {e}")
    except Exception as e:
        raise HTTPException(401, f"Authentication failed: {e}")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[UserInfo]:
    """Like get_current_user but returns None instead of 401 if no token."""
    if _DEV_MODE:
        return UserInfo(
            clerk_user_id="dev_user_001",
            email="dev@localhost",
            first_name="Dev",
            last_name="User",
        )

    if not credentials:
        return None

    try:
        jwks = await _get_jwks()
        unverified_header = jwt.get_unverified_header(credentials.credentials)
        kid = unverified_header.get("kid")

        key_data = None
        for k in jwks:
            if k.get("kid") == kid:
                key_data = k
                break

        if not key_data:
            return None

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

        payload = jwt.decode(
            credentials.credentials,
            public_key,
            algorithms=["RS256"],
            issuer=f"https://{settings.clerk_domain}",
            options={"verify_aud": False},
        )

        return UserInfo(
            clerk_user_id=payload.get("sub", ""),
            email=payload.get("email", ""),
            first_name=payload.get("first_name", ""),
            last_name=payload.get("last_name", ""),
        )
    except Exception:
        return None
