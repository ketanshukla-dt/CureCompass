from types import SimpleNamespace

import pytest

from api.config import get_settings
from api.llm import LLMConfigError, LLMError, get_llm_provider
from api.llm.anthropic_provider import AnthropicProvider
from api.llm.ollama_provider import OllamaProvider


def _fake_client(*, stop_reason="end_turn", blocks=None):
    blocks = [SimpleNamespace(type="text", text='{"ok": true}')] if blocks is None else blocks

    async def create(**_kwargs):
        return SimpleNamespace(stop_reason=stop_reason, content=blocks)

    return SimpleNamespace(messages=SimpleNamespace(create=create))


def _provider(client) -> AnthropicProvider:
    provider = AnthropicProvider.__new__(AnthropicProvider)
    provider.name, provider._model, provider._client = "anthropic", "test-model", client
    return provider


async def _complete(provider):
    return await provider.complete(system="s", prompt="p", max_tokens=10)


# ── provider selection ────────────────────────────────────────────────────────
def test_anthropic_without_key_is_a_config_error():
    with pytest.raises(LLMConfigError, match="ANTHROPIC_API_KEY"):
        get_llm_provider()


def test_placeholder_key_is_rejected(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-XXXXXXXX")
    get_settings.cache_clear()
    with pytest.raises(LLMConfigError):
        get_llm_provider()


def test_real_looking_key_builds_provider(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-realistic-looking-key")
    get_settings.cache_clear()
    assert get_llm_provider().name == "anthropic"


def test_ollama_needs_no_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    get_settings.cache_clear()
    assert isinstance(get_llm_provider(), OllamaProvider)


def test_vertex_requires_project(monkeypatch):
    pytest.importorskip("anthropic")
    monkeypatch.setenv("LLM_PROVIDER", "vertex")
    get_settings.cache_clear()
    with pytest.raises(LLMConfigError):
        get_llm_provider()


# ── AnthropicProvider.complete ────────────────────────────────────────────────
async def test_complete_returns_text():
    assert await _complete(_provider(_fake_client())) == '{"ok": true}'


async def test_complete_rejects_truncated_output():
    with pytest.raises(LLMError, match="truncated"):
        await _complete(_provider(_fake_client(stop_reason="max_tokens")))


async def test_complete_rejects_empty_output():
    with pytest.raises(LLMError, match="empty"):
        await _complete(_provider(_fake_client(blocks=[])))


async def test_complete_wraps_sdk_errors_without_leaking_details():
    async def boom(**_kwargs):
        raise RuntimeError("secret upstream detail https://internal.example")

    client = SimpleNamespace(messages=SimpleNamespace(create=boom))
    with pytest.raises(LLMError) as excinfo:
        await _complete(_provider(client))
    assert "internal.example" not in str(excinfo.value)
