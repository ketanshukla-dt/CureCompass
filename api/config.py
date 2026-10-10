from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    dt_tenant_url: str = ""
    dt_api_token: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    simulation_mode: bool = False
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Always read from .env — never use OS-level cached env vars
        env_file_override = True


# Cached: .env is parsed once per process; restart the server to pick up changes.
@lru_cache
def get_settings() -> Settings:
    return Settings()
