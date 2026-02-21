from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from openai import APIError, APITimeoutError, AzureOpenAI, RateLimitError

from backend.models.schemas import AnomalyResponse
from backend.utils.config import Settings, get_settings

SYSTEM_PROMPT = """You are a forensic audit copilot.
Return ONLY valid JSON with this schema:
{
  "explanation": "string",
  "risk_level": "Low|Medium|High",
  "possible_cause": "string",
  "recommended_action": "string"
}
Keep recommendations practical and compliance-focused.
"""


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client: AzureOpenAI | None = None

        if settings.llm_provider == "azure":
            self.client = AzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint,
            )

    async def explain_anomaly(self, anomaly: AnomalyResponse) -> dict[str, str]:
        if self.settings.llm_provider == "azure":
            return await self._with_retries(self._explain_with_azure, anomaly)
        if self.settings.llm_provider == "ollama":
            return await self._with_retries(self._explain_with_ollama, anomaly)

        raise RuntimeError("Unsupported LLM provider. Use 'azure' or 'ollama'.")

    async def _with_retries(self, fn, anomaly: AnomalyResponse) -> dict[str, str]:
        delays = [1, 2, 4]
        for idx, delay in enumerate(delays, start=1):
            try:
                return await fn(anomaly)
            except (RateLimitError, APITimeoutError) as exc:
                if idx == len(delays):
                    raise RuntimeError(f"LLM request failed after retries: {exc}") from exc
                await asyncio.sleep(delay)
            except APIError as exc:
                raise RuntimeError(f"LLM API error: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSON from LLM: {exc}") from exc

        raise RuntimeError("Unreachable retry state")

    async def _explain_with_azure(self, anomaly: AnomalyResponse) -> dict[str, str]:
        if not self.client:
            raise RuntimeError("Azure OpenAI client is not configured")

        user_prompt = self._build_user_prompt(anomaly)

        def _call() -> dict[str, str]:
            response = self.client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            return self._normalize_output(parsed)

        return await asyncio.to_thread(_call)

    async def _explain_with_ollama(self, anomaly: AnomalyResponse) -> dict[str, str]:
        payload = {
            "model": self.settings.ollama_model,
            "prompt": f"{SYSTEM_PROMPT}\nTransaction JSON:\n{json.dumps(anomaly.model_dump(), ensure_ascii=True)}",
            "format": "json",
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.settings.ollama_base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()

        raw = data.get("response", "{}")
        parsed = json.loads(raw)
        return self._normalize_output(parsed)

    @staticmethod
    def _build_user_prompt(anomaly: AnomalyResponse) -> str:
        return (
            "Analyze this flagged ledger transaction and provide concise audit guidance.\n"
            f"Transaction JSON: {json.dumps(anomaly.model_dump(), ensure_ascii=True)}"
        )

    @staticmethod
    def _normalize_output(payload: dict[str, Any]) -> dict[str, str]:
        risk = str(payload.get("risk_level", "Medium")).capitalize()
        if risk not in {"Low", "Medium", "High"}:
            risk = "Medium"
        return {
            "explanation": str(payload.get("explanation", "No explanation returned.")),
            "risk_level": risk,
            "possible_cause": str(payload.get("possible_cause", "Unknown")),
            "recommended_action": str(payload.get("recommended_action", "Review transaction and supporting documents.")),
        }


def get_llm_service() -> LLMService:
    return LLMService(get_settings())
