from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    dt_tenant_url: str = ""
    dt_api_token: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    simulation_mode: bool = False
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Always read from .env — never use OS-level cached env vars
        env_file_override = True


# NOTE: No @lru_cache here — always reload from .env on each call.
# This ensures that changing .env and restarting picks up the new values.
def get_settings() -> Settings:
    return Settings()
