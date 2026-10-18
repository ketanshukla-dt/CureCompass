from typing import Annotated

from fastapi import APIRouter, Query

from api import database

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
async def get_history(limit: Annotated[int, Query(ge=1, le=500)] = 50):
    """Remediation history log, newest first."""
    return await database.get_history(limit)


@router.get("/stats")
async def get_stats():
    """Aggregated remediation statistics."""
    return await database.get_history_stats()
