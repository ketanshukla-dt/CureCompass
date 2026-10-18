from api.config import get_settings


def test_healthz_reports_mode_without_secrets(client):
    body = client.get("/healthz").json()
    assert body == {
        "status": "ok",
        "mode": "SIMULATION",
        "dynatrace": "mock",
        "llm_provider": "anthropic",
    }


def test_list_incidents(client):
    incidents = client.get("/api/incidents").json()
    assert len(incidents) == 4
    assert {i["status"] for i in incidents} == {"OPEN"}


def test_unknown_incident_is_404(client):
    assert client.get("/api/incidents/NOPE-1").status_code == 404


def test_malformed_incident_id_is_rejected(client):
    assert client.get("/api/incidents/bad.id").status_code == 422
    assert client.post("/api/incidents/bad.id/analyze").status_code == 422


def test_analyze_marks_incident_ready_and_caches(client):
    result = client.post("/api/incidents/P-DEMO-001/analyze").json()
    assert result["status"] == "REMEDIATION_READY"
    assert result["analysis"]["scripts"]

    # Second call is served from the cache: identical script ids.
    again = client.post("/api/incidents/P-DEMO-001/analyze").json()
    assert [s["id"] for s in again["analysis"]["scripts"]] == [
        s["id"] for s in result["analysis"]["scripts"]
    ]

    # `force` re-runs the analysis, producing fresh script ids.
    forced = client.post("/api/incidents/P-DEMO-001/analyze?force=true").json()
    assert forced["analysis"]["scripts"][0]["id"] != result["analysis"]["scripts"][0]["id"]


def test_list_flags_analyzed_incidents(client):
    client.post("/api/incidents/P-DEMO-002/analyze")
    by_id = {i["id"]: i["status"] for i in client.get("/api/incidents").json()}
    assert by_id["P-DEMO-002"] == "REMEDIATION_READY"
    assert by_id["P-DEMO-001"] == "OPEN"


def test_get_incident_attaches_cached_analysis(client):
    client.post("/api/incidents/P-DEMO-003/analyze")
    incident = client.get("/api/incidents/P-DEMO-003").json()
    assert incident["analysis"] is not None


def test_resolve_records_history_and_stats(client):
    body = {"script_id": "Rollback", "outcome": "success", "notes": "worked"}
    assert client.post("/api/incidents/P-DEMO-004/resolve", json=body).status_code == 200

    history = client.get("/api/history").json()
    assert history[0]["outcome"] == "success"
    stats = client.get("/api/history/stats").json()
    assert (stats["total"], stats["success"], stats["failed"]) == (1, 1, 0)


def test_resolve_rejects_invalid_outcome_and_long_notes(client):
    url = "/api/incidents/P-DEMO-004/resolve"
    assert client.post(url, json={"script_id": "x", "outcome": "maybe"}).status_code == 422
    too_long = {"script_id": "x", "outcome": "success", "notes": "n" * 2001}
    assert client.post(url, json=too_long).status_code == 422


def test_validate_in_simulation_mode(client):
    result = client.post("/api/incidents/P-DEMO-001/validate").json()
    assert result["recovery_confirmed"] is True


def test_live_llm_without_key_returns_actionable_503(client, monkeypatch):
    monkeypatch.setenv("SIMULATION_MODE", "false")
    get_settings.cache_clear()
    # No DT token -> mock incidents still load, but the LLM call needs a key.
    response = client.post("/api/incidents/P-DEMO-001/analyze")
    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]
