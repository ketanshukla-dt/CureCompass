from fastapi import APIRouter, HTTPException, Path
from api.models import AIAnalysis, Incident, ResolveRequest, IncidentStatus
from api.dynatrace import get_incidents, get_incident_by_id
from api.ai_engine import analyze_incident, validate_resolution as ai_validate
from api import database
import json
import logging
from datetime import datetime, timezone
from typing import Annotated

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

# Dynatrace problem IDs are alphanumeric with "_" and "-". Rejecting everything else
# stops path-traversal style input from reaching the upstream API URL.
IncidentId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_\-]{1,100}$")]


async def _load_incident(incident_id: str) -> Incident:
    """Fetch an incident, mapping upstream failures to a safe 502 / 404."""
    try:
        incident = await get_incident_by_id(incident_id)
    except Exception:
        logger.exception("Failed to fetch incident %s from Dynatrace", incident_id)
        raise HTTPException(status_code=502, detail="Failed to reach Dynatrace")
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("", response_model=list[Incident])
async def list_incidents():
    """Fetch all active + recent incidents from Dynatrace (or simulation)."""
    try:
        return await get_incidents()
    except Exception:
        logger.exception("Failed to fetch incidents from Dynatrace")
        raise HTTPException(status_code=502, detail="Failed to reach Dynatrace")


@router.get("/{incident_id}", response_model=Incident)
async def get_incident(incident_id: IncidentId):
    """Get a single incident with all details."""
    incident = await _load_incident(incident_id)

    # Attach cached analysis if available
    cached = await database.get_cached_analysis(incident_id)
    if cached:
        try:
            incident.analysis = AIAnalysis(**json.loads(cached))
            incident.status = IncidentStatus.REMEDIATION_READY
        except Exception:
            logger.warning("Ignoring corrupt cached analysis for %s", incident_id)

    return incident


@router.post("/{incident_id}/analyze", response_model=Incident)
async def trigger_analysis(incident_id: IncidentId):
    """
    🤖 AI TOUCHPOINT 1 & 2 & 3 & 5:
    Claude performs root cause analysis, recommends remediation,
    generates scripts, and writes step-by-step execution guidance.
    """
    incident = await _load_incident(incident_id)

    incident.status = IncidentStatus.ANALYZING

    # Run AI analysis (Claude)
    try:
        analysis = await analyze_incident(incident)
    except Exception:
        logger.exception("AI analysis failed for %s", incident_id)
        raise HTTPException(status_code=502, detail="AI analysis failed. Check server logs.")
    incident.analysis = analysis
    incident.status = IncidentStatus.REMEDIATION_READY

    # Cache the analysis
    await database.save_analysis(
        incident_id,
        analysis.model_dump_json()
    )

    return incident


@router.post("/{incident_id}/resolve")
async def resolve_incident(incident_id: IncidentId, body: ResolveRequest):
    """Record the outcome after the customer runs a remediation script."""
    incident = await _load_incident(incident_id)

    # Ensure subtraction is timezone-aware
    now_utc = datetime.now(timezone.utc)
    start_time_utc = incident.start_time.astimezone(timezone.utc)
    duration = int((now_utc - start_time_utc).total_seconds() / 60)

    await database.record_resolution(
        incident_id=incident_id,
        incident_title=incident.title,
        script_title=body.script_id,
        outcome=body.outcome,
        notes=body.notes,
        duration_minutes=duration
    )

    return {"status": "recorded", "outcome": body.outcome}


@router.post("/{incident_id}/validate")
async def validate_resolution(incident_id: IncidentId):
    """
    🤖 AI TOUCHPOINT 6:
    Claude checks the post-fix state and confirms whether the
    incident metrics indicate a successful recovery.
    """
    incident = await _load_incident(incident_id)

    try:
        return await ai_validate(incident)
    except Exception:
        logger.exception("AI validation failed for %s", incident_id)
        raise HTTPException(status_code=502, detail="AI validation failed. Check server logs.")
