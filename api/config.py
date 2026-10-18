from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProviderName = Literal["anthropic", "bedrock", "vertex", "ollama"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Dynatrace ────────────────────────────────────────────────────────────
    dt_tenant_url: str = ""
    dt_api_token: str = ""
    simulation_mode: bool = False

    # ── LLM provider ─────────────────────────────────────────────────────────
    llm_provider: LLMProviderName = "anthropic"
    llm_timeout_seconds: float = 60.0
    # Model id for the chosen provider (Bedrock/Vertex use their own id formats).
    anthropic_model: str = "claude-sonnet-5-5"
    anthropic_api_key: str = ""
    aws_region: str = "us-east-1"            # bedrock (credentials come from the AWS chain)
    vertex_project_id: str = ""              # vertex (credentials come from gcloud ADC)
    vertex_region: str = "us-east5"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # ── Server ───────────────────────────────────────────────────────────────
    port: int = 8000
    # Loopback by default. Use 0.0.0.0 only behind an authenticating reverse proxy:
    # the app itself has no login.
    host: str = "127.0.0.1"
    # Comma-separated browser origins allowed for CORS. The built SPA is same-origin
    # and needs none; this is for the Vite dev server.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ── Storage ──────────────────────────────────────────────────────────────
    database_path: str = "incidents.db"
    analysis_cache_ttl_minutes: int = 1440

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def dynatrace_is_live(self) -> bool:
        """True when real Dynatrace data should be used instead of mock incidents."""
        return not self.simulation_mode and bool(self.dt_api_token)


# Cached: .env is parsed once per process; restart the server to pick up changes.
# Real OS environment variables take precedence over .env (pydantic-settings default).
@lru_cache
def get_settings() -> Settings:
    return Settings()
