import pytest
from fastapi.testclient import TestClient

from api.config import get_settings
from api.llm import get_llm_provider


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_llm_provider.cache_clear()


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Every test runs in simulation mode against a throwaway database."""
    monkeypatch.setenv("SIMULATION_MODE", "true")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("DT_API_TOKEN", "")
    monkeypatch.setenv("DT_TENANT_URL", "")
    _clear_caches()
    yield
    _clear_caches()


@pytest.fixture
def client():
    from main import app

    with TestClient(app) as test_client:
        yield test_client
