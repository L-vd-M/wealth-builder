import os
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

_security = HTTPBearer(auto_error=False)
_jwks_cache: dict | None = None


async def _fetch_jwks() -> dict:
    global _jwks_cache  # noqa: PLW0603
    if _jwks_cache is not None:
        return _jwks_cache
    jwks_url = os.getenv("CLERK_JWKS_URL", "")
    if not jwks_url:
        raise HTTPException(status_code=503, detail="Auth not configured (CLERK_JWKS_URL missing)")
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url, timeout=10.0)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache  # type: ignore[return-value]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_security)] = None,
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    try:
        jwks = await _fetch_jwks()
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        keys: list[dict] = jwks.get("keys", [])
        key = next((k for k in keys if k.get("kid") == kid), keys[0] if keys else None)
        if key is None:
            raise HTTPException(status_code=401, detail="No valid signing key found")
        payload = jwt.decode(token, key, algorithms=["RS256"], options={"leeway": 10})
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_security)] = None,
) -> str | None:
    """Return user_id when a valid Bearer token is present, None otherwise."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
