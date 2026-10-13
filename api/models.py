from pydantic import BaseModel, Field
from typing import Literal, Optional, List
from enum import Enum
from datetime import datetime


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    ANALYZING = "ANALYZING"
    REMEDIATION_READY = "REMEDIATION_READY"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class RiskLevel(str, Enum):
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
    rollback_script: Optional[str] = None


class ExecutionStep(BaseModel):
    step_number: int
    title: str
    instruction: str
    command: Optional[str] = None
    expected_outcome: str
    is_validation: bool = False


class AIAnalysis(BaseModel):
    root_cause: str
    confidence: int            # 0-100
    impact_summary: str
    recommended_action: str
    scripts: List[RemediationScript]
    execution_steps: List[ExecutionStep]
    post_fix_checks: List[str]
    analysis_timestamp: datetime


class Incident(BaseModel):
    id: str
    title: str
    severity: Severity
    status: IncidentStatus
    incident_type: str         # cpu_memory | service_crash | db_slowness | deployment_rollback | monitoring_gap
    affected_entities: List[AffectedEntity]
    start_time: datetime
    duration_minutes: int
    impact_count: int
    raw_details: dict
    analysis: Optional[AIAnalysis] = None


class ResolveRequest(BaseModel):
    script_id: str = Field(max_length=100)
    notes: Optional[str] = Field(default=None, max_length=2000)
    outcome: Literal["success", "partial", "failed"]


class RemediationRecord(BaseModel):
    id: int
    incident_id: str
    incident_title: str
    script_title: str
    outcome: str
    notes: Optional[str]
    resolved_at: datetime
    duration_minutes: int
