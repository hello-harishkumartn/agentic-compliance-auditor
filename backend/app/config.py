from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agentic Compliance Auditor"
    database_url: str = "sqlite:///./compliance.db"
    llm_provider: str = "deterministic"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    max_agent_iterations: int = 12
    min_compliant_confidence: float = 0.82
    auto_seed: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
