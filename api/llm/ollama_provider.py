"""Local models through Ollama's OpenAI-compatible endpoint (no key, data stays local)."""

import httpx

from api.config import Settings
from api.llm.base import LLMError


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self._url = f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"
        self._model = settings.ollama_model
        self._timeout = settings.llm_timeout_seconds

    async def complete(self, *, system: str, prompt: str, max_tokens: int) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(self._url, json=payload)
                resp.raise_for_status()
                choice = resp.json()["choices"][0]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"ollama request failed: {type(exc).__name__}") from exc

        if choice.get("finish_reason") == "length":
            raise LLMError("LLM response was truncated (max_tokens reached)")
        text = (choice.get("message") or {}).get("content") or ""
        if not text.strip():
            raise LLMError("LLM returned an empty response")
        return text
