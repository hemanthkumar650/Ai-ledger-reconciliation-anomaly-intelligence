from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    cors_origins: list[str] = ["*"]

    anomalies_csv_path: str = "backend/data/Synthetic Accounting Financial Dataset.csv"

    llm_provider: str = "azure"  # azure | ollama

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_deployment: str = ""

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    api_key: str = ""
    api_keys: dict[str, str] = {}
    risk_score_by_account: dict[str, float] = {}
    risk_score_by_category: dict[str, float] = {}
    risk_level_high_cutoff: float = 0.85
    risk_level_medium_cutoff: float = 0.6


@lru_cache
def get_settings() -> Settings:
    return Settings()
