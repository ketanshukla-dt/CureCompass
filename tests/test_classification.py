import pytest

from api.dynatrace import _classify_incident


@pytest.mark.parametrize(
    "title,expected",
    [
        ("CPU saturation on production web tier", "cpu_memory"),
        ("Kubernetes pod crashlooping — payment-service", "service_crash"),
        ("Database connection pool exhaustion — orders-db", "db_slowness"),
        ("Error rate spike after v2.4.1 deployment — user-api", "deployment_rollback"),
        ("Synthetic private location outage", "monitoring_gap"),
        ("ActiveGate unavailable", "monitoring_gap"),
        # Whole-word matching: substrings must not trigger a category.
        ("User feedback form slow", "service_crash"),
        ("Markdown renderer latency", "service_crash"),
        ("Unrecognised problem", "service_crash"),
    ],
)
def test_classify_by_title(title, expected):
    assert _classify_incident({"title": title}) == expected


def test_monitoring_gap_detected_from_event_type():
    problem = {
        "title": "Something odd",
        "evidenceDetails": {"details": [{"eventType": "SYNTHETIC_NODE_OUTAGE"}]},
    }
    assert _classify_incident(problem) == "monitoring_gap"
