from __future__ import annotations

from fastapi import Header, HTTPException

from backend.utils.config import get_settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    configured = settings.api_key.strip()
    if not configured:
        return

    if x_api_key != configured:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
