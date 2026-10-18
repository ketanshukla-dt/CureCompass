"""Provider-neutral LLM interface."""

from typing import Protocol


class LLMError(Exception):
    """The LLM call failed or returned unusable output."""


class LLMConfigError(LLMError):
    """The selected LLM provider is not configured (missing key, project, etc.)."""


class LLMProvider(Protocol):
    """Anything that can turn a system + user prompt into reply text."""

    name: str

    async def complete(self, *, system: str, prompt: str, max_tokens: int) -> str:
        """Return the model's text reply. Raise LLMError on failure."""
        ...
