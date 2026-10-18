import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from api import database
from api.ai_engine import analyze_incident
from api.ai_engine import validate_resolution as ai_validate
from api.dynatrace import get_incident_by_id, get_incidents
from api.llm import LLMConfigError, LLMError
from api.models import AIAnalysis, Incident, IncidentStatus, ResolveRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

# Dynatrace problem IDs are alphanumeric with "_" and "-". Rejecting everything else
# stops path-traversal style input from reaching the upstream API URL.
IncidentId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_\-]{1,100}$")]

# One analysis per incident at a time, so concurrent clicks cost one LLM call.
_analysis_locks: dict[str, asyncio.Lock] = {}


async def _load_incident(incident_id: str) -> Incident:
    """Fetch an incident, mapping upstream failures to a safe 502 / 404."""
    try:
        incident = await get_incident_by_id(incident_id)
    except Exception as exc:
        logger.exception("Failed to fetch incident %s from Dynatrace", incident_id)
        raise HTTPException(status_code=502, detail="Failed to reach Dynatrace") from exc
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


def _parse_cached(cached: str | None) -> AIAnalysis | None:
    if not cached:
        return None
    try:
        return AIAnalysis(**json.loads(cached))
    except Exception:
        logger.warning("Ignoring corrupt cached analysis")
        return None


def _attach_analysis(incident: Incident, analysis: AIAnalysis) -> Incident:
    incident.analysis = analysis
    incident.status = IncidentStatus.REMEDIATION_READY
    return incident


def _llm_http_error(exc: Exception, what: str) -> HTTPException:
    """Map LLM failures to HTTP errors without leaking provider internals."""
    if isinstance(exc, LLMConfigError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=502, detail=f"{what} failed. Check server logs.")


@router.get("", response_model=list[Incident])
async def list_incidents():
    """Fetch active incidents from Dynatrace (or simulation), flagging cached analyses."""
    try:
        incidents = await get_incidents()
    except Exception as exc:
        logger.exception("Failed to fetch incidents from Dynatrace")
        raise HTTPException(status_code=502, detail="Failed to reach Dynatrace") from exc

    analyzed = await database.get_cached_incident_ids()
    for incident in incidents:
        if incident.id in analyzed:
            incident.status = IncidentStatus.REMEDIATION_READY
    return incidents


@router.get("/{incident_id}", response_model=Incident)
async def get_incident(incident_id: IncidentId):
    """Get a single incident, with its cached analysis if there is one."""
    incident = await _load_incident(incident_id)
    analysis = _parse_cached(await database.get_cached_analysis(incident_id))
    return _attach_analysis(incident, analysis) if analysis else incident


@router.post("/{incident_id}/analyze", response_model=Incident)
async def trigger_analysis(
    incident_id: IncidentId,
    force: Annotated[bool, Query(description="Ignore the cache; re-run the analysis")] = False,
):
    """
    AI touchpoints 1-5: root cause explanation, recommended fix, scripts,
    risk assessment and step-by-step execution guidance. Cached unless `force`.
    """
    incident = await _load_incident(incident_id)

    async with _analysis_locks.setdefault(incident_id, asyncio.Lock()):
        if not force:
            cached = _parse_cached(await database.get_cached_analysis(incident_id))
            if cached:
                return _attach_analysis(incident, cached)

        try:
            analysis = await analyze_incident(incident)
        except (LLMError, ValueError, KeyError) as exc:
            logger.exception("AI analysis failed for %s", incident_id)
            raise _llm_http_error(exc, "AI analysis") from exc
        await database.save_analysis(incident_id, analysis.model_dump_json())

    return _attach_analysis(incident, analysis)


@router.post("/{incident_id}/resolve")
async def resolve_incident(incident_id: IncidentId, body: ResolveRequest):
    """Record the outcome after the customer runs a remediation script."""
    incident = await _load_incident(incident_id)

    elapsed = datetime.now(UTC) - incident.start_time.astimezone(UTC)
    await database.record_resolution(
        incident_id=incident_id,
        incident_title=incident.title,
        script_title=body.script_id,
        outcome=body.outcome,
        notes=body.notes,
        duration_minutes=int(elapsed.total_seconds() / 60),
    )
    return {"status": "recorded", "outcome": body.outcome}


@router.post("/{incident_id}/validate")
async def validate_resolution(incident_id: IncidentId):
    """AI touchpoint 6: judge whether the incident looks recovered after the fix."""
    incident = await _load_incident(incident_id)
    try:
        return await ai_validate(incident)
    except (LLMError, ValueError, KeyError) as exc:
        logger.exception("AI validation failed for %s", incident_id)
        raise _llm_http_error(exc, "AI validation") from exc
