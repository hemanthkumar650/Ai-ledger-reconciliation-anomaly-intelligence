from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from openai import APIError, APITimeoutError, AzureOpenAI, RateLimitError

from backend.models.schemas import AnomalyResponse
from backend.utils.config import Settings, get_settings
from backend.utils.metrics import metrics_store

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

REPORT_SYSTEM_PROMPT = """You are a senior audit manager.
Generate a concise audit report for flagged ledger transactions.
Focus on material risks, likely root causes, and practical actions.
"""

CHAT_SYSTEM_PROMPT = """You are an audit assistant.
Answer only from provided ledger context. If not in context, say so clearly.
Keep responses concise and actionable.
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
        provider = self.settings.llm_provider
        metrics_store.increment_llm_call(provider)
        delays = [1, 2, 4]
        for idx, delay in enumerate(delays, start=1):
            try:
                return await fn(anomaly)
            except (RateLimitError, APITimeoutError) as exc:
                if idx == len(delays):
                    metrics_store.increment_llm_failure(provider)
                    raise RuntimeError(f"LLM request failed after retries: {exc}") from exc
                metrics_store.increment_llm_retry(provider)
                await asyncio.sleep(delay)
            except APIError as exc:
                metrics_store.increment_llm_failure(provider)
                raise RuntimeError(f"LLM API error: {exc}") from exc
            except json.JSONDecodeError as exc:
                metrics_store.increment_llm_failure(provider)
                raise RuntimeError(f"Invalid JSON from LLM: {exc}") from exc

        raise RuntimeError("Unreachable retry state")

    async def generate_audit_report(self, anomalies: list[AnomalyResponse]) -> str:
        context = self._build_dataset_context(anomalies, max_rows=50)
        prompt = (
            "Create an audit summary with sections: "
            "1) Executive Summary, 2) Key Risks, 3) Probable Causes, 4) Recommended Actions.\n"
            f"Dataset context:\n{context}"
        )
        return await self._text_completion(REPORT_SYSTEM_PROMPT, prompt)

    async def chat_with_ledger(self, question: str, anomalies: list[AnomalyResponse], max_rows: int = 30) -> str:
        context = self._build_dataset_context(anomalies, max_rows=max_rows)
        prompt = f"Ledger context:\n{context}\n\nUser question: {question}"
        return await self._text_completion(CHAT_SYSTEM_PROMPT, prompt)

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

    async def _text_completion(self, system_prompt: str, user_prompt: str) -> str:
        provider = self.settings.llm_provider
        metrics_store.increment_llm_call(provider)
        if self.settings.llm_provider == "azure":
            try:
                return await self._text_with_azure(system_prompt, user_prompt)
            except RuntimeError:
                metrics_store.increment_llm_failure(provider)
                raise
        if self.settings.llm_provider == "ollama":
            try:
                return await self._text_with_ollama(system_prompt, user_prompt)
            except RuntimeError:
                metrics_store.increment_llm_failure(provider)
                raise
        raise RuntimeError("Unsupported LLM provider. Use 'azure' or 'ollama'.")

    async def _text_with_azure(self, system_prompt: str, user_prompt: str) -> str:
        if not self.client:
            raise RuntimeError("Azure OpenAI client is not configured")

        def _call() -> str:
            response = self.client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            return (response.choices[0].message.content or "").strip()

        try:
            return await asyncio.to_thread(_call)
        except (RateLimitError, APITimeoutError) as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc
        except APIError as exc:
            raise RuntimeError(f"LLM API error: {exc}") from exc

    async def _text_with_ollama(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.settings.ollama_model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.settings.ollama_base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        return str(data.get("response", "")).strip()

    @staticmethod
    def _build_user_prompt(anomaly: AnomalyResponse) -> str:
        sanitized = LLMService._sanitize_payload(anomaly.model_dump())
        return (
            "Analyze this flagged ledger transaction and provide concise audit guidance.\n"
            f"Transaction JSON: {json.dumps(sanitized, ensure_ascii=True)}"
        )

    @staticmethod
    def _build_dataset_context(anomalies: list[AnomalyResponse], max_rows: int) -> str:
        if not anomalies:
            return "No flagged transactions found."

        subset = anomalies[:max_rows]
        lines: list[str] = []
        for item in subset:
            lines.append(
                f"tx={item.transaction_id}, amount={item.amount}, account={item.account}, "
                f"score={item.anomaly_score}, risk={item.risk_level}"
            )
        return "\n".join(lines)

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

    @staticmethod
    def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        sensitive_tokens = {"email", "phone", "ssn", "tax", "iban", "swift", "account_number", "bank_account"}

        def _sanitize(value: Any, key: str | None = None) -> Any:
            if key and any(token in key.lower() for token in sensitive_tokens):
                return "[REDACTED]"
            if isinstance(value, dict):
                return {k: _sanitize(v, k) for k, v in value.items()}
            if isinstance(value, list):
                return [_sanitize(item, key) for item in value]
            return value

        return _sanitize(payload)


def get_llm_service() -> LLMService:
    return LLMService(get_settings())
