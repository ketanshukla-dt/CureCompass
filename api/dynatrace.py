"""
Dynatrace Integration Layer
===========================
Fetches problems from Dynatrace Problems v2 API.
Davis AI's root cause analysis is embedded in each problem payload —
we extract it and pass it to Claude for remediation guidance.

Simulation mode provides realistic mock data for offline demos.
"""

import re
from datetime import UTC, datetime
from urllib.parse import quote

import httpx

from api.config import get_settings
from api.models import AffectedEntity, Incident, IncidentStatus, Severity

# ── Severity mapping ──────────────────────────────────────────────────────────
_SEVERITY_MAP = {
    "AVAILABILITY": Severity.CRITICAL,
    "ERROR": Severity.HIGH,
    "PERFORMANCE": Severity.MEDIUM,
    "RESOURCE_CONTENTION": Severity.MEDIUM,
    "CUSTOM_ALERT": Severity.LOW,
}

# ── Incident type detection (from DT problem title / impact areas) ────────────
def _keyword_regex(*keywords: str) -> re.Pattern:
    """Whole-word match, so 'db' never matches 'feedback' or 'down' 'markdown'."""
    return re.compile(r"\b(?:" + "|".join(keywords) + r")\b", re.IGNORECASE)


# Monitoring-infrastructure problems (ActiveGates, synthetic locations, agents) must be
# checked first: they are not application/Kubernetes failures.
_MONITORING_GAP = _keyword_regex(
    "activegate", "synthetic", "monitoring not available", "oneagent", "extension",
    "node_outage", "location outage",
)
# Event types are machine tokens like SYNTHETIC_NODE_OUTAGE (underscores join words),
# so they need substring matching rather than whole-word matching.
_MONITORING_EVENT_TOKENS = ("activegate", "synthetic", "oneagent", "extension", "node_outage")
# Ordered: first match wins.
_TITLE_RULES: list[tuple[str, re.Pattern]] = [
    ("cpu_memory", _keyword_regex("cpu", "memory", "heap", "resource")),
    (
        "service_crash",
        _keyword_regex("crash\\w*", "restart\\w*", "unavailable", "down", "pod\\w*"),
    ),
    ("db_slowness", _keyword_regex("database", "db", "query", "connection pool", "sql")),
    ("deployment_rollback", _keyword_regex("deploy\\w*", "rollback", "error rate", "spike")),
]


def _classify_incident(problem: dict) -> str:
    title = problem.get("title") or ""
    event_types = " ".join(_event_types(problem)).lower()

    if _MONITORING_GAP.search(title) or any(t in event_types for t in _MONITORING_EVENT_TOKENS):
        return "monitoring_gap"
    for incident_type, pattern in _TITLE_RULES:
        if pattern.search(title):
            return incident_type
    return "service_crash"


def _event_types(problem: dict) -> list[str]:
    details = (problem.get("evidenceDetails") or {}).get("details") or []
    return sorted({d["eventType"] for d in details if d.get("eventType")})


def _parse_entity(entity: dict) -> AffectedEntity:
    return AffectedEntity(
        entity_id=entity.get("entityId", {}).get("id", "unknown"),
        entity_name=entity.get("name", "unknown"),
        entity_type=entity.get("entityId", {}).get("type", "UNKNOWN"),
    )


def _evidence_names(problem: dict) -> list[str]:
    details = (problem.get("evidenceDetails") or {}).get("details") or []
    return [d["displayName"] for d in details if d.get("displayName")]


def _comment_texts(problem: dict) -> list[str]:
    comments = (problem.get("recentComments") or {}).get("comments") or []
    return [c["content"] for c in comments if c.get("content")]


def _dt_to_incident(problem: dict) -> Incident:
    start_ms = problem.get("startTime", 0)
    end_ms = problem.get("endTime", 0)
    start_dt = datetime.fromtimestamp(start_ms / 1000, tz=UTC)

    if end_ms and end_ms > 0:  # Dynatrace uses -1 for still-open problems
        end_dt = datetime.fromtimestamp(end_ms / 1000, tz=UTC)
        duration = int((end_dt - start_dt).total_seconds() / 60)
    else:
        duration = int((datetime.now(UTC) - start_dt).total_seconds() / 60)

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
            # Davis AI root cause — passed to the LLM for remediation
            "davis_root_cause": problem.get("rootCauseEntity"),
            "davis_impact_level": problem.get("impactLevel"),
            "display_id": problem.get("displayId"),
            "davis_event_types": _event_types(problem),
            "evidence": _evidence_names(problem),
            "comments": _comment_texts(problem),
            "affected_entity_names": [e.entity_name for e in entities],
            "problem_filters": problem.get("problemFilters", []),
            "management_zones": [mz.get("name") for mz in problem.get("managementZones", [])],
        },
    )


def _get_base_url(tenant_url: str) -> str:
    url = tenant_url.strip()
    if "/api/" in url:
        url = url.split("/api/")[0]
    return url.rstrip("/")


# ── Live Dynatrace fetch ──────────────────────────────────────────────────────
_PROBLEM_FIELDS = "+affectedEntities,+rootCauseEntity,+recentComments,+evidenceDetails"


def _live_request_args(path: str) -> tuple[str, dict]:
    settings = get_settings()
    headers = {
        "Authorization": f"Api-Token {settings.dt_api_token}",
        "Content-Type": "application/json",
    }
    return f"{_get_base_url(settings.dt_tenant_url)}/api/v2/{path}", headers


async def _fetch_live_incidents(max_pages: int = 10) -> list[Incident]:
    url, headers = _live_request_args("problems")
    # Dynatrace caps pageSize at 10 when `fields` is set, so follow nextPageKey.
    # A nextPageKey request must not repeat the original query parameters.
    params = {
        "problemSelector": "status(OPEN)",
        "fields": _PROBLEM_FIELDS,
        "pageSize": 10,
    }
    problems: list[dict] = []

    async with httpx.AsyncClient(timeout=15) as client:
        for _ in range(max_pages):
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            problems.extend(data.get("problems", []))
            next_key = data.get("nextPageKey")
            if not next_key:
                break
            params = {"nextPageKey": next_key}

    return [_dt_to_incident(p) for p in problems]


async def _fetch_live_incident(problem_id: str) -> Incident | None:
    # Never let user input alter the API path (blocks "../entities" style traversal).
    url, headers = _live_request_args(f"problems/{quote(problem_id, safe='')}")
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
        "startTime": int((datetime.now(UTC).timestamp() - 3600) * 1000),
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
        "startTime": int((datetime.now(UTC).timestamp() - 1800) * 1000),
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
        "startTime": int((datetime.now(UTC).timestamp() - 900) * 1000),
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
        "startTime": int((datetime.now(UTC).timestamp() - 600) * 1000),
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
    if not get_settings().dynatrace_is_live:
        return _mock_incidents()
    return await _fetch_live_incidents()


async def get_incident_by_id(problem_id: str) -> Incident | None:
    if not get_settings().dynatrace_is_live:
        return _mock_incident(problem_id)
    return await _fetch_live_incident(problem_id)
