from api import database
from api.config import get_settings


async def test_cached_analysis_round_trip():
    await database.init_db()
    await database.save_analysis("P-1", '{"a": 1}')
    assert await database.get_cached_analysis("P-1") == '{"a": 1}'
    assert await database.get_cached_incident_ids() == {"P-1"}


async def test_expired_cache_is_ignored(monkeypatch):
    await database.init_db()
    await database.save_analysis("P-1", "{}")
    monkeypatch.setenv("ANALYSIS_CACHE_TTL_MINUTES", "-1")
    get_settings.cache_clear()
    assert await database.get_cached_analysis("P-1") is None
    assert await database.get_cached_incident_ids() == set()


async def test_stats_on_empty_history():
    await database.init_db()
    assert await database.get_history_stats() == {
        "total": 0, "success": 0, "partial": 0, "failed": 0, "avg_resolution_minutes": 0,
    }


async def test_stats_average_counts_only_successes():
    await database.init_db()
    await database.record_resolution("a", "A", "s", "success", None, 10)
    await database.record_resolution("b", "B", "s", "success", None, 20)
    await database.record_resolution("c", "C", "s", "failed", None, 500)
    stats = await database.get_history_stats()
    assert (stats["total"], stats["success"], stats["failed"]) == (3, 2, 1)
    assert stats["avg_resolution_minutes"] == 15.0
