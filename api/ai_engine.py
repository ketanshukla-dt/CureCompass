"""
AI Engine
=========
The intelligence layer that sits on top of Davis AI.

Davis AI (Dynatrace) tells us WHAT broke and WHY.
The LLM (Claude by default) tells us HOW to fix it — safely, step-by-step.

Six AI touchpoints:
  1. Fix Recommendation    — best remediation action with explanation
  2. Script Generation     — restart / rollback / cache-clear / scaling scripts
  3. Risk Assessment       — low/medium/high risk with reasoning per script
  4. Natural Language      — Davis's technical data in plain English
  5. Execution Guidance    — numbered step-by-step guide with pre/post checks
  6. Resolution Validation — confirm metrics recovered after the fix

The model backend is pluggable: see api/llm (anthropic | bedrock | vertex | ollama).
"""

from api import fixtures
from api.analysis import build_analysis, parse_json_response
from api.config import get_settings
from api.llm import get_llm_provider
from api.models import AIAnalysis, Incident
from api.prompts import (
    RECOMMENDATION_PROMPT,
    SYSTEM_PROMPT,
    VALIDATION_PROMPT,
    build_context,
)

ANALYSIS_MAX_TOKENS = 4096
VALIDATION_MAX_TOKENS = 1024


async def _ask_llm(prompt: str, max_tokens: int) -> dict:
    reply = await get_llm_provider().complete(
        system=SYSTEM_PROMPT, prompt=prompt, max_tokens=max_tokens
    )
    return parse_json_response(reply)


async def analyze_incident(incident: Incident) -> AIAnalysis:
    """AI touchpoints 1-5: recommendation, scripts, risk, plain English, execution guide."""
    if get_settings().simulation_mode:
        return fixtures.mock_analysis(incident)

    prompt = RECOMMENDATION_PROMPT.format(context=build_context(incident))
    return build_analysis(await _ask_llm(prompt, ANALYSIS_MAX_TOKENS))


async def validate_resolution(incident: Incident) -> dict:
    """AI touchpoint 6: judge whether the incident looks recovered after the fix."""
    if get_settings().simulation_mode:
        return fixtures.mock_validation(incident)

    prompt = VALIDATION_PROMPT.format(context=build_context(incident))
    return await _ask_llm(prompt, VALIDATION_MAX_TOKENS)
