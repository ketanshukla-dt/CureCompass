"""
Dynatrace Integration Layer
===========================
Fetches problems from Dynatrace Problems v2 API.
Davis AI's root cause analysis is embedded in each problem payload —
we extract it and pass it to Claude for remediation guidance.

Simulation mode provides realistic mock data for offline demos.
"""

import httpx
from datetime import datetime, timezone
from api.config import get_settings
from api.models import (
    Incident, IncidentStatus, Severity, AffectedEntity
)


# ── Severity mapping ──────────────────────────────────────────────────────────
_SEVERITY_MAP = {
    "AVAILABILITY": Severity.CRITICAL,
    "ERROR": Severity.HIGH,
    "PERFORMANCE": Severity.MEDIUM,
    "RESOURCE_CONTENTION": Severity.MEDIUM,
    "CUSTOM_ALERT": Severity.LOW,
}

# ── Incident type detection (from DT problem title / impact areas) ────────────
def _classify_incident(problem: dict) -> str:
    title = (problem.get("title") or "").lower()

    if any(k in title for k in ["cpu", "memory", "heap", "resource"]):
        return "cpu_memory"
    if any(k in title for k in ["crash", "restart", "unavailable", "down", "pod"]):
        return "service_crash"
    if any(k in title for k in ["database", "db", "query", "connection pool", "sql"]):
        return "db_slowness"
    if any(k in title for k in ["deployment", "deploy", "rollback", "error rate", "spike"]):
        return "deployment_rollback"
    return "service_crash"


def _parse_entity(entity: dict) -> AffectedEntity:
    return AffectedEntity(
        entity_id=entity.get("entityId", {}).get("id", "unknown"),
        entity_name=entity.get("name", "unknown"),
        entity_type=entity.get("entityId", {}).get("type", "UNKNOWN"),
    )


def _dt_to_incident(problem: dict) -> Incident:
    start_ms = problem.get("startTime", 0)
    end_ms   = problem.get("endTime", 0)
    start_dt = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)

    if end_ms:
        end_dt = datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)
        duration = int((end_dt - start_dt).total_seconds() / 60)
    else:
        duration = int((datetime.now(timezone.utc) - start_dt).total_seconds() / 60)

    entities = [_parse_entity(e) for e in problem.get("affectedEntities", [])]
    severity = _SEVERITY_MAP.get(problem.get("severityLevel", ""), Severity.MEDIUM)

    status_raw = problem.get("status", "OPEN")
    status = IncidentStatus.OPEN if status_raw == "OPEN" else IncidentStatus.RESOLVED

    return Incident(
        id=problem["problemId"],
        title=problem.get("title", "Unknown Problem"),
        severity=severity,
        status=status,
        incident_type=_classify_incident(problem),
        affected_entities=entities,
        start_time=start_dt,
        duration_minutes=duration,
        impact_count=len(entities),
        raw_details={
            # Davis AI root cause — passed to Claude for remediation
            "davis_root_cause":     problem.get("rootCauseEntity"),
            "davis_impact_level":   problem.get("impactLevel"),
            "davis_event_types":    [e.get("eventType") for e in problem.get("recentComments", {}).get("comments", [])],
            "affected_entity_names": [e.entity_name for e in entities],
            "problem_filters":      problem.get("problemFilters", []),
            "management_zones":     [mz.get("name") for mz in problem.get("managementZones", [])],
        }
    )


def _get_base_url(tenant_url: str) -> str:
    url = tenant_url.strip()
    if "/api/" in url:
        url = url.split("/api/")[0]
    return url.rstrip("/")


# ── Live Dynatrace fetch ──────────────────────────────────────────────────────
_PROBLEM_FIELDS = "+affectedEntities,+rootCauseEntity,+recentComments"


def _live_request_args(path: str) -> tuple[str, dict]:
    settings = get_settings()
    headers = {
        "Authorization": f"Api-Token {settings.dt_api_token}",
        "Content-Type": "application/json",
    }
    return f"{_get_base_url(settings.dt_tenant_url)}/api/v2/{path}", headers


async def _fetch_live_incidents() -> list[Incident]:
    url, headers = _live_request_args("problems")
    params = {
        "problemSelector": "status(OPEN)",
        "fields": _PROBLEM_FIELDS,
        "pageSize": 50,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

    return [_dt_to_incident(p) for p in data.get("problems", [])]


async def _fetch_live_incident(problem_id: str) -> Incident | None:
    url, headers = _live_request_args(f"problems/{problem_id}")
    params = {"fields": _PROBLEM_FIELDS}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _dt_to_incident(resp.json())


# ── Simulation / mock data ────────────────────────────────────────────────────
_MOCK_INCIDENTS: list[dict] = [
    {
        "problemId": "P-DEMO-001",
        "title": "CPU saturation on production web tier",
        "severityLevel": "AVAILABILITY",
        "status": "OPEN",
        "impactLevel": "SERVICE",
        "startTime": int((datetime.now(timezone.utc).timestamp() - 3600) * 1000),
        "endTime": 0,
        "affectedEntities": [
            {"entityId": {"id": "HOST-001", "type": "HOST"}, "name": "prod-web-01"},
            {"entityId": {"id": "HOST-002", "type": "HOST"}, "name": "prod-web-02"},
        ],
        "rootCauseEntity": {"id": "HOST-001", "type": "HOST", "name": "prod-web-01"},
        "recentComments": {"comments": []},
        "managementZones": [{"name": "Production"}],
    },
    {
        "problemId": "P-DEMO-002",
        "title": "Kubernetes pod crashlooping — payment-service",
        "severityLevel": "ERROR",
        "status": "OPEN",
        "impactLevel": "SERVICE",
        "startTime": int((datetime.now(timezone.utc).timestamp() - 1800) * 1000),
        "endTime": 0,
        "affectedEntities": [
            {"entityId": {"id": "SVC-001", "type": "SERVICE"}, "name": "payment-service"},
            {"entityId": {"id": "SVC-002", "type": "SERVICE"}, "name": "checkout-api"},
        ],
        "rootCauseEntity": {"id": "SVC-001", "type": "SERVICE", "name": "payment-service"},
        "recentComments": {"comments": []},
        "managementZones": [{"name": "Production"}],
    },
    {
        "problemId": "P-DEMO-003",
        "title": "Database connection pool exhaustion — orders-db",
        "severityLevel": "PERFORMANCE",
        "status": "OPEN",
        "impactLevel": "SERVICE",
        "startTime": int((datetime.now(timezone.utc).timestamp() - 900) * 1000),
        "endTime": 0,
        "affectedEntities": [
            {"entityId": {"id": "DB-001", "type": "SERVICE"}, "name": "orders-db"},
            {"entityId": {"id": "SVC-003", "type": "SERVICE"}, "name": "orders-service"},
        ],
        "rootCauseEntity": {"id": "DB-001", "type": "SERVICE", "name": "orders-db"},
        "recentComments": {"comments": []},
        "managementZones": [{"name": "Production"}],
    },
    {
        "problemId": "P-DEMO-004",
        "title": "Error rate spike after v2.4.1 deployment — user-api",
        "severityLevel": "ERROR",
        "status": "OPEN",
        "impactLevel": "SERVICE",
        "startTime": int((datetime.now(timezone.utc).timestamp() - 600) * 1000),
        "endTime": 0,
        "affectedEntities": [
            {"entityId": {"id": "SVC-004", "type": "SERVICE"}, "name": "user-api"},
        ],
        "rootCauseEntity": {"id": "SVC-004", "type": "SERVICE", "name": "user-api"},
        "recentComments": {"comments": []},
        "managementZones": [{"name": "Production"}],
    },
]


def _mock_incidents() -> list[Incident]:
    return [_dt_to_incident(p) for p in _MOCK_INCIDENTS]


def _mock_incident(problem_id: str) -> Incident | None:
    hit = next((p for p in _MOCK_INCIDENTS if p["problemId"] == problem_id), None)
    return _dt_to_incident(hit) if hit else None


# ── Public API ────────────────────────────────────────────────────────────────
async def get_incidents() -> list[Incident]:
    settings = get_settings()
    if settings.simulation_mode or not settings.dt_api_token:
        return _mock_incidents()
    return await _fetch_live_incidents()


async def get_incident_by_id(problem_id: str) -> Incident | None:
    settings = get_settings()
    if settings.simulation_mode or not settings.dt_api_token:
        return _mock_incident(problem_id)
    return await _fetch_live_incident(problem_id)
