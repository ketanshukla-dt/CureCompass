import aiosqlite
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("incidents.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
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
            "CREATE INDEX IF NOT EXISTS idx_history_resolved_at ON remediation_history (resolved_at DESC)"
        )
        await db.commit()


async def save_analysis(incident_id: str, analysis_json: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO analysis_cache (incident_id, analysis_json, cached_at) VALUES (?, ?, ?)",
            (incident_id, analysis_json, datetime.now(timezone.utc).isoformat())
        )
        await db.commit()


async def get_cached_analysis(incident_id: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT analysis_json FROM analysis_cache WHERE incident_id = ?",
            (incident_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def record_resolution(
    incident_id: str,
    incident_title: str,
    script_title: str,
    outcome: str,
    notes: str | None,
    duration_minutes: int
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO remediation_history
               (incident_id, incident_title, script_title, outcome, notes, resolved_at, duration_minutes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (incident_id, incident_title, script_title, outcome,
             notes, datetime.now(timezone.utc).isoformat(), duration_minutes)
        )
        await db.commit()


async def get_history(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM remediation_history ORDER BY resolved_at DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_history_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT outcome, COUNT(*) as count FROM remediation_history GROUP BY outcome"
        ) as cursor:
            rows = await cursor.fetchall()
            stats = {row[0]: row[1] for row in rows}

        async with db.execute(
            "SELECT AVG(duration_minutes) FROM remediation_history WHERE outcome = 'success'"
        ) as cursor:
            row = await cursor.fetchone()
            avg_duration = round(row[0] or 0, 1)

    return {
        "total": sum(stats.values()),
        "success": stats.get("success", 0),
        "partial": stats.get("partial", 0),
        "failed": stats.get("failed", 0),
        "avg_resolution_minutes": avg_duration
    }
