import argparse
import json
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.utils.config import get_settings


def _ok(name: str, detail: str) -> dict[str, str | bool]:
    return {"name": name, "ok": True, "detail": detail}


def _fail(name: str, detail: str) -> dict[str, str | bool]:
    return {"name": name, "ok": False, "detail": detail}


def run_checks() -> tuple[bool, list[dict[str, str | bool]]]:
    settings = get_settings()
    checks: list[dict[str, str | bool]] = []

    dataset_path = Path(settings.anomalies_csv_path)
    if dataset_path.exists():
        checks.append(_ok("dataset", f"Found at {dataset_path.as_posix()}"))
    else:
        checks.append(_fail("dataset", f"Missing file at {dataset_path.as_posix()}"))

    provider = settings.llm_provider.strip().lower()
    if provider == "azure":
        missing: list[str] = []
        if not settings.azure_openai_endpoint.strip():
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not settings.azure_openai_api_key.strip():
            missing.append("AZURE_OPENAI_API_KEY")
        if not settings.azure_openai_deployment.strip():
            missing.append("AZURE_OPENAI_DEPLOYMENT")
        if missing:
            checks.append(_fail("llm", f"Provider=azure, missing: {', '.join(missing)}"))
        else:
            checks.append(_ok("llm", "Provider=azure, required config present"))
    elif provider == "ollama":
        base_url = settings.ollama_base_url.strip()
        model_name = settings.ollama_model.strip()
        if not base_url or not model_name:
            checks.append(_fail("llm", "Provider=ollama, missing OLLAMA_BASE_URL or OLLAMA_MODEL"))
        else:
            try:
                response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
                response.raise_for_status()
                payload = response.json()
                models = payload.get("models", [])
                installed = {str(item.get("name", "")).strip() for item in models if isinstance(item, dict)}
                if model_name in installed:
                    checks.append(_ok("llm", f"Provider=ollama, model '{model_name}' installed"))
                else:
                    available = ", ".join(sorted(name for name in installed if name)) or "none"
                    checks.append(
                        _fail("llm", f"Provider=ollama, model '{model_name}' missing. Available: {available}")
                    )
            except httpx.HTTPError as exc:
                checks.append(_fail("llm", f"Provider=ollama, check failed: {exc}"))
    else:
        checks.append(_fail("llm", f"Unsupported LLM_PROVIDER '{settings.llm_provider}'"))

    passed = all(bool(item["ok"]) for item in checks)
    return passed, checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate local AuditAI environment before startup.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    passed, checks = run_checks()
    if args.json:
        print(json.dumps({"ready": passed, "checks": checks}, ensure_ascii=True))
    else:
        for item in checks:
            prefix = "[OK]" if item["ok"] else "[FAIL]"
            print(f"{prefix} {item['name']}: {item['detail']}")
        print("READY" if passed else "NOT READY")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
