import asyncio
import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.utils.config import Settings, get_settings


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: run async tests with asyncio.run")


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    if not inspect.iscoroutinefunction(pyfuncitem.obj):
        return None

    test_args = {
        name: pyfuncitem.funcargs[name]
        for name in pyfuncitem._fixtureinfo.argnames
        if name in pyfuncitem.funcargs
    }
    asyncio.run(pyfuncitem.obj(**test_args))
    return True


@pytest.fixture(autouse=True)
def _isolate_settings_from_dotenv():
    original_env_file = Settings.model_config.get("env_file")
    Settings.model_config["env_file"] = None
    get_settings.cache_clear()
    try:
        yield
    finally:
        if original_env_file is None:
            Settings.model_config.pop("env_file", None)
        else:
            Settings.model_config["env_file"] = original_env_file
        get_settings.cache_clear()
