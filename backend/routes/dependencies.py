from __future__ import annotations

from collections.abc import Callable

from fastapi import Header, HTTPException

from backend.utils.config import get_settings


def _normalize_role(role: str) -> str:
    normalized = role.strip().lower()
    return normalized if normalized in {"admin", "auditor"} else "auditor"


async def get_auth_role(x_api_key: str | None = Header(default=None)) -> str:
    settings = get_settings()
    configured_map = {k.strip(): _normalize_role(v) for k, v in settings.api_keys.items() if k.strip()}
    if configured_map:
        if not x_api_key or x_api_key not in configured_map:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        return configured_map[x_api_key]

    configured = settings.api_key.strip()
    if configured:
        if x_api_key != configured:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        return "admin"

    return "anonymous"


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    await get_auth_role(x_api_key)


def require_role(*allowed_roles: str) -> Callable:
    allowed = {_normalize_role(role) for role in allowed_roles}

    async def _dependency(x_api_key: str | None = Header(default=None)) -> None:
        role = await get_auth_role(x_api_key)
        if role == "anonymous":
            return
        if role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")

    return _dependency
