from fastapi import APIRouter, HTTPException, BackgroundTasks
from api.models import Incident, ResolveRequest, IncidentStatus
from api.dynatrace import get_incidents, get_incident_by_id
from api.ai_engine import analyze_incident
from api import database
from api.config import get_settings
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=list[Incident])
async def list_incidents():
    """Fetch all active + recent incidents from Dynatrace (or simulation)."""
    settings = get_settings()
    logger.info(f"[Incidents] SIMULATION_MODE={settings.simulation_mode}")
    logger.info(f"[Incidents] DT_TENANT_URL={settings.dt_tenant_url}")
    logger.info(f"[Incidents] DT_API_TOKEN={'***' + settings.dt_api_token[-6:] if settings.dt_api_token else '(empty)'}")
    try:
        return await get_incidents()
    except Exception as exc:
        logger.error(f"[Incidents] Failed to fetch from Dynatrace: {exc}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach Dynatrace: {str(exc)}"
        )


@router.get("/{incident_id}", response_model=Incident)
async def get_incident(incident_id: str):
    """Get a single incident with all details."""
    incident = await get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Attach cached analysis if available
    cached = await database.get_cached_analysis(incident_id)
    if cached:
        from api.models import AIAnalysis
        incident.analysis = AIAnalysis(**json.loads(cached))
        incident.status = IncidentStatus.REMEDIATION_READY

    return incident


@router.post("/{incident_id}/analyze", response_model=Incident)
async def trigger_analysis(incident_id: str):
    """
    🤖 AI TOUCHPOINT 1 & 2 & 3 & 5:
    Claude performs root cause analysis, recommends remediation,
    generates scripts, and writes step-by-step execution guidance.
    """
    incident = await get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident.status = IncidentStatus.ANALYZING

    # Run AI analysis (Claude)
    analysis = await analyze_incident(incident)
    incident.analysis = analysis
    incident.status = IncidentStatus.REMEDIATION_READY

    # Cache the analysis
    await database.save_analysis(
        incident_id,
        analysis.model_dump_json()
    )

    return incident


@router.post("/{incident_id}/resolve")
async def resolve_incident(incident_id: str, body: ResolveRequest):
    """Record the outcome after the customer runs a remediation script."""
    incident = await get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

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
async def validate_resolution(incident_id: str):
    """
    🤖 AI TOUCHPOINT 6:
    Claude checks the post-fix state and confirms whether the
    incident metrics indicate a successful recovery.
    """
    from api.ai_engine import validate_resolution as ai_validate
    incident = await get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    result = await ai_validate(incident)
    return result
