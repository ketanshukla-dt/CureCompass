from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    dt_tenant_url: str = ""
    dt_api_token: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    simulation_mode: bool = False
    port: int = 8000
    # Bind to loopback by default. Set HOST=0.0.0.0 only behind an authenticating
    # reverse proxy / SSO — the app itself has no login.
    host: str = "127.0.0.1"
    # Comma-separated browser origins allowed to call the API cross-origin.
    # The built SPA is served same-origin and needs no CORS; this is for the Vite dev server.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Cached: .env is parsed once per process; restart the server to pick up changes.
# Note: real OS environment variables take precedence over .env (standard pydantic-settings behaviour).
@lru_cache
def get_settings() -> Settings:
    return Settings()
