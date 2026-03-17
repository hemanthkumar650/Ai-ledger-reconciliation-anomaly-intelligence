import pytest
from fastapi import HTTPException

from backend.routes.dependencies import get_auth_role, require_api_key
from backend.utils.config import get_settings


@pytest.mark.asyncio
async def test_get_auth_role_rejects_missing_api_key_for_configured_key_map(monkeypatch):
    monkeypatch.setenv("API_KEYS", '{"auditor-key":"auditor"}')
    monkeypatch.delenv("API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(HTTPException, match="Invalid or missing API key") as exc_info:
        await get_auth_role(None)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_api_key_accepts_valid_key_from_configured_key_map(monkeypatch):
    monkeypatch.setenv("API_KEYS", '{"auditor-key":"auditor"}')
    monkeypatch.delenv("API_KEY", raising=False)
    get_settings.cache_clear()

    assert await require_api_key("auditor-key") is None
