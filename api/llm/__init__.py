"""LLM provider selection. Choose with LLM_PROVIDER in .env."""

from functools import lru_cache

from api.config import get_settings
from api.llm.anthropic_provider import AnthropicProvider
from api.llm.base import LLMConfigError, LLMError, LLMProvider
from api.llm.ollama_provider import OllamaProvider

__all__ = ["LLMConfigError", "LLMError", "LLMProvider", "get_llm_provider"]


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Build the configured provider once per process (restart to change)."""
    settings = get_settings()
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings)
    return AnthropicProvider(settings, variant=settings.llm_provider)
