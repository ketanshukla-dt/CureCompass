"""Turn raw LLM output into validated domain models."""

import json
import uuid
from datetime import UTC, datetime

from api.models import AIAnalysis, ExecutionStep, RemediationScript, RiskLevel
from api.safety import RISK_FLAG_PREFIX, is_risky_script


def parse_json_response(raw: str) -> dict:
    """Extract the JSON object from a model reply, tolerating fences and prose."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("LLM response did not contain a JSON object")
    return json.loads(raw[start : end + 1])


def _build_script(data: dict) -> RemediationScript:
    risk_level = RiskLevel(data["risk_level"].lower())
    risk_reason = data["risk_reason"]
    if is_risky_script(data["script"]):
        # A destructive-looking script must never be presented as low risk.
        risk_level = RiskLevel.HIGH
        risk_reason = f"{RISK_FLAG_PREFIX} {risk_reason}"
    return RemediationScript(
        id=str(uuid.uuid4()),
        title=data["title"],
        description=data["description"],
        language=data["language"],
        script=data["script"],
        risk_level=risk_level,
        risk_reason=risk_reason,
        estimated_downtime=data["estimated_downtime"],
        rollback_script=data.get("rollback_script"),
    )


def _build_step(data: dict) -> ExecutionStep:
    return ExecutionStep(
        step_number=data["step_number"],
        title=data["title"],
        instruction=data["instruction"],
        command=data.get("command"),
        expected_outcome=data["expected_outcome"],
        is_validation=data.get("is_validation", False),
    )


def build_analysis(data: dict) -> AIAnalysis:
    """Build an AIAnalysis from the recommendation JSON (live model or fixture)."""
    return AIAnalysis(
        root_cause=data.get("explanation", ""),
        confidence=max(0, min(100, int(data.get("confidence", 80)))),
        impact_summary=data.get("impact_summary", ""),
        recommended_action=data.get("recommended_action", ""),
        scripts=[_build_script(s) for s in data.get("scripts", [])],
        execution_steps=[_build_step(s) for s in data.get("execution_steps", [])],
        post_fix_checks=data.get("post_fix_checks", []),
        analysis_timestamp=datetime.now(UTC),
    )
