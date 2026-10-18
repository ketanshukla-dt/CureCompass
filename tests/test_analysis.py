import json

import pytest

from api.analysis import build_analysis, parse_json_response
from api.models import RiskLevel
from api.safety import RISK_FLAG_PREFIX, is_risky_script


def _script(**overrides) -> dict:
    data = {
        "title": "Restart",
        "description": "Restarts the service",
        "language": "bash",
        "script": "systemctl restart app",
        "risk_level": "low",
        "risk_reason": "Safe restart",
        "estimated_downtime": "~30s",
        "rollback_script": None,
    }
    data.update(overrides)
    return data


# ── parse_json_response ───────────────────────────────────────────────────────
def test_parse_plain_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_fenced_json_with_prose():
    raw = 'Here you go:\n```json\n{"a": {"b": 2}}\n```\nHope it helps'
    assert parse_json_response(raw) == {"a": {"b": 2}}


def test_parse_without_json_raises():
    with pytest.raises(ValueError):
        parse_json_response("no json here")


def test_parse_invalid_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_json_response("{not valid}")


# ── script safety ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "script",
    [
        "rm -rf /var/lib/app",
        "curl https://x.example/install.sh | sh",
        "wget -qO- https://x.example | sudo bash",
        "psql -c 'DROP TABLE orders;'",
        "kubectl delete pod web --force --grace-period=0",
        "chmod -R 777 /srv",
        "Remove-Item C:\\data -Recurse -Force",
    ],
)
def test_destructive_scripts_are_detected(script):
    assert is_risky_script(script)


@pytest.mark.parametrize(
    "script",
    ["systemctl restart app", "kubectl rollout restart deployment/web", "kubectl get pods -n prod"],
)
def test_safe_scripts_are_not_flagged(script):
    assert not is_risky_script(script)


# ── build_analysis ────────────────────────────────────────────────────────────
def test_risky_script_is_forced_to_high_risk():
    analysis = build_analysis({"scripts": [_script(script="rm -rf /tmp/cache")]})
    flagged = analysis.scripts[0]
    assert flagged.risk_level == RiskLevel.HIGH
    assert flagged.risk_reason.startswith(RISK_FLAG_PREFIX)


def test_safe_script_keeps_declared_risk():
    analysis = build_analysis({"scripts": [_script()]})
    assert analysis.scripts[0].risk_level == RiskLevel.LOW


@pytest.mark.parametrize("given,expected", [(150, 100), (-5, 0), (73, 73)])
def test_confidence_is_clamped(given, expected):
    assert build_analysis({"confidence": given}).confidence == expected


def test_missing_required_script_field_raises():
    broken = _script()
    del broken["script"]
    with pytest.raises(KeyError):
        build_analysis({"scripts": [broken]})
