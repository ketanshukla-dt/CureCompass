from fastapi import APIRouter
from api import database

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
async def get_history():
    """Get remediation history log."""
    records = await database.get_history()
    return records


@router.get("/stats")
async def get_stats():
    """Get aggregated remediation statistics."""
    return await database.get_history_stats()
