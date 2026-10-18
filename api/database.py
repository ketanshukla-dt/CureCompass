"""SQLite storage: remediation history and the analysis cache."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiosqlite

from api.config import get_settings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BUSY_TIMEOUT_MS = 5000


def _db_path() -> Path:
    """DATABASE_PATH, resolved against the project root (not the working directory)."""
    path = Path(get_settings().database_path)
    return path if path.is_absolute() else _PROJECT_ROOT / path


@asynccontextmanager
async def _connect():
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
        yield db


async def init_db() -> None:
    async with _connect() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS remediation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL,
                incident_title TEXT NOT NULL,
                script_title TEXT NOT NULL,
                outcome TEXT NOT NULL,
                notes TEXT,
                resolved_at TEXT NOT NULL,
                duration_minutes INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analysis_cache (
                incident_id TEXT PRIMARY KEY,
                analysis_json TEXT NOT NULL,
                cached_at TEXT NOT NULL
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_resolved_at "
            "ON remediation_history (resolved_at DESC)"
        )
        await db.commit()


def _cache_cutoff() -> str:
    ttl = timedelta(minutes=get_settings().analysis_cache_ttl_minutes)
    return (datetime.now(UTC) - ttl).isoformat()


async def save_analysis(incident_id: str, analysis_json: str) -> None:
    async with _connect() as db:
        await db.execute(
            "INSERT OR REPLACE INTO analysis_cache (incident_id, analysis_json, cached_at) "
            "VALUES (?, ?, ?)",
            (incident_id, analysis_json, datetime.now(UTC).isoformat()),
        )
        await db.commit()


async def get_cached_analysis(incident_id: str) -> str | None:
    """Cached analysis JSON, or None if missing or older than the cache TTL."""
    async with _connect() as db:
        async with db.execute(
            "SELECT analysis_json FROM analysis_cache WHERE incident_id = ? AND cached_at >= ?",
            (incident_id, _cache_cutoff()),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_cached_incident_ids() -> set[str]:
    """IDs of incidents that have a fresh cached analysis."""
    async with _connect() as db:
        async with db.execute(
            "SELECT incident_id FROM analysis_cache WHERE cached_at >= ?", (_cache_cutoff(),)
        ) as cursor:
            return {row[0] for row in await cursor.fetchall()}


async def record_resolution(
    incident_id: str,
    incident_title: str,
    script_title: str,
    outcome: str,
    notes: str | None,
    duration_minutes: int,
) -> None:
    async with _connect() as db:
        await db.execute(
            """INSERT INTO remediation_history
               (incident_id, incident_title, script_title, outcome, notes,
                resolved_at, duration_minutes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (incident_id, incident_title, script_title, outcome,
             notes, datetime.now(UTC).isoformat(), duration_minutes),
        )
        await db.commit()


async def get_history(limit: int = 50) -> list[dict]:
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM remediation_history ORDER BY resolved_at DESC LIMIT ?", (limit,)
        ) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


async def get_history_stats() -> dict:
    async with _connect() as db:
        async with db.execute(
            """SELECT COUNT(*),
                      COALESCE(SUM(outcome = 'success'), 0),
                      COALESCE(SUM(outcome = 'partial'), 0),
                      COALESCE(SUM(outcome = 'failed'), 0),
                      AVG(CASE WHEN outcome = 'success' THEN duration_minutes END)
               FROM remediation_history"""
        ) as cursor:
            total, success, partial, failed, avg_duration = await cursor.fetchone()

    return {
        "total": total,
        "success": success,
        "partial": partial,
        "failed": failed,
        "avg_resolution_minutes": round(avg_duration or 0, 1),
    }
