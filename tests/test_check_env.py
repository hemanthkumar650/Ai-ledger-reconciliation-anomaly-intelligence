import httpx

import ops.check_env as check_env
from backend.utils.config import get_settings


def _existing_dataset_path() -> str:
    return "backend/data/Synthetic Accounting Financial Dataset.csv"


def test_run_checks_passes_for_valid_azure_config(monkeypatch):
    monkeypatch.setenv("ANOMALIES_CSV_PATH", _existing_dataset_path())
    monkeypatch.setenv("LLM_PROVIDER", "azure")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "deployment")
    get_settings.cache_clear()

    ready, checks = check_env.run_checks()

    assert ready is True
    assert checks[0]["name"] == "dataset"
    assert checks[0]["ok"] is True
    assert checks[1]["name"] == "llm"
    assert checks[1]["ok"] is True


def test_run_checks_fails_for_missing_dataset(monkeypatch):
    monkeypatch.setenv("ANOMALIES_CSV_PATH", "backend/data/does-not-exist.csv")
    monkeypatch.setenv("LLM_PROVIDER", "azure")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "deployment")
    get_settings.cache_clear()

    ready, checks = check_env.run_checks()

    assert ready is False
    assert checks[0]["name"] == "dataset"
    assert checks[0]["ok"] is False


def test_run_checks_fails_for_missing_azure_config(monkeypatch):
    monkeypatch.setenv("ANOMALIES_CSV_PATH", _existing_dataset_path())
    monkeypatch.setenv("LLM_PROVIDER", "azure")
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    get_settings.cache_clear()

    ready, checks = check_env.run_checks()

    assert ready is False
    assert checks[1]["name"] == "llm"
    assert checks[1]["ok"] is False
    assert "missing" in str(checks[1]["detail"]).lower()


def test_run_checks_passes_for_ollama_when_model_installed(monkeypatch):
    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": [{"name": "qwen2:0.5b"}]}

    monkeypatch.setenv("ANOMALIES_CSV_PATH", _existing_dataset_path())
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2:0.5b")
    get_settings.cache_clear()
    monkeypatch.setattr(check_env.httpx, "get", lambda *_args, **_kwargs: _FakeResponse())

    ready, checks = check_env.run_checks()

    assert ready is True
    assert checks[1]["name"] == "llm"
    assert checks[1]["ok"] is True


def test_run_checks_fails_for_ollama_when_model_missing(monkeypatch):
    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": [{"name": "qwen2:0.5b"}]}

    monkeypatch.setenv("ANOMALIES_CSV_PATH", _existing_dataset_path())
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1")
    get_settings.cache_clear()
    monkeypatch.setattr(check_env.httpx, "get", lambda *_args, **_kwargs: _FakeResponse())

    ready, checks = check_env.run_checks()

    assert ready is False
    assert checks[1]["name"] == "llm"
    assert checks[1]["ok"] is False
    assert "missing" in str(checks[1]["detail"]).lower()


def test_run_checks_fails_for_ollama_http_error(monkeypatch):
    monkeypatch.setenv("ANOMALIES_CSV_PATH", _existing_dataset_path())
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2:0.5b")
    get_settings.cache_clear()

    def _raise_http_error(*_args, **_kwargs):
        raise httpx.HTTPError("connection failed")

    monkeypatch.setattr(check_env.httpx, "get", _raise_http_error)

    ready, checks = check_env.run_checks()

    assert ready is False
    assert checks[1]["name"] == "llm"
    assert checks[1]["ok"] is False
    assert "check failed" in str(checks[1]["detail"]).lower()
