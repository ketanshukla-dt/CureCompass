from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    ANALYZING = "ANALYZING"
    REMEDIATION_READY = "REMEDIATION_READY"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AffectedEntity(BaseModel):
    entity_id: str
    entity_name: str
    entity_type: str


class RemediationScript(BaseModel):
    id: str
    title: str
    description: str
    language: str          # bash | powershell | kubectl | python
    script: str
    risk_level: RiskLevel
    risk_reason: str
    estimated_downtime: str
    rollback_script: str | None = None


class ExecutionStep(BaseModel):
    step_number: int
    title: str
    instruction: str
    command: str | None = None
    expected_outcome: str
    is_validation: bool = False


class AIAnalysis(BaseModel):
    root_cause: str
    confidence: int            # 0-100
    impact_summary: str
    recommended_action: str
    scripts: list[RemediationScript]
    execution_steps: list[ExecutionStep]
    post_fix_checks: list[str]
    analysis_timestamp: datetime


class Incident(BaseModel):
    id: str
    title: str
    severity: Severity
    status: IncidentStatus
    # cpu_memory | service_crash | db_slowness | deployment_rollback | monitoring_gap
    incident_type: str
    affected_entities: list[AffectedEntity]
    start_time: datetime
    duration_minutes: int
    impact_count: int
    raw_details: dict
    analysis: AIAnalysis | None = None


class ResolveRequest(BaseModel):
    script_id: str = Field(max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    outcome: Literal["success", "partial", "failed"]


class RemediationRecord(BaseModel):
    id: int
    incident_id: str
    incident_title: str
    script_title: str
    outcome: str
    notes: str | None
    resolved_at: datetime
    duration_minutes: int
