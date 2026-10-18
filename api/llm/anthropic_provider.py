"""Claude via the Anthropic SDK: direct API, Amazon Bedrock, or Google Vertex AI."""

from api.config import Settings
from api.llm.base import LLMConfigError, LLMError

_PLACEHOLDER_KEY_MARKERS = ("sk-ant-XXX", "YOUR_ANTHROPIC", "sk-ant-placeholder")


def _has_real_key(key: str) -> bool:
    key = key.strip()
    return bool(key) and not any(marker in key for marker in _PLACEHOLDER_KEY_MARKERS)


def _build_client(settings: Settings, variant: str):
    timeout = settings.llm_timeout_seconds
    if variant == "anthropic":
        from anthropic import AsyncAnthropic

        if not _has_real_key(settings.anthropic_api_key):
            raise LLMConfigError(
                "ANTHROPIC_API_KEY is not configured. Add a real key to .env, "
                "or set LLM_PROVIDER=bedrock|vertex|ollama, or enable SIMULATION_MODE."
            )
        return AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=timeout, max_retries=2)

    if variant == "bedrock":
        try:
            from anthropic import AsyncAnthropicBedrock
        except ImportError as exc:  # pragma: no cover - depends on installed extras
            raise LLMConfigError('Bedrock needs: pip install "anthropic[bedrock]"') from exc
        return AsyncAnthropicBedrock(aws_region=settings.aws_region, timeout=timeout, max_retries=2)

    if variant == "vertex":
        try:
            from anthropic import AsyncAnthropicVertex
        except ImportError as exc:  # pragma: no cover - depends on installed extras
            raise LLMConfigError('Vertex needs: pip install "anthropic[vertex]"') from exc
        if not settings.vertex_project_id:
            raise LLMConfigError("VERTEX_PROJECT_ID is not configured.")
        return AsyncAnthropicVertex(
            project_id=settings.vertex_project_id,
            region=settings.vertex_region,
            timeout=timeout,
            max_retries=2,
        )

    raise LLMConfigError(f"Unknown Anthropic variant: {variant}")


class AnthropicProvider:
    """Calls Claude through any of the SDK's transports; same Messages API for all."""

    def __init__(self, settings: Settings, variant: str = "anthropic") -> None:
        self.name = variant
        self._model = settings.anthropic_model
        self._client = _build_client(settings, variant)

    async def complete(self, *, system: str, prompt: str, max_tokens: int) -> str:
        try:
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise LLMError(f"{self.name} request failed: {type(exc).__name__}") from exc

        if message.stop_reason == "max_tokens":
            raise LLMError("LLM response was truncated (max_tokens reached)")
        text = "".join(b.text for b in message.content if getattr(b, "type", "") == "text")
        if not text.strip():
            raise LLMError("LLM returned an empty response")
        return text
