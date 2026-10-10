"""
AI Engine — Powered by Claude (Anthropic)
==========================================
This is the intelligence layer that sits on top of Davis AI.

Davis AI (Dynatrace) tells us WHAT broke and WHY.
Claude tells us HOW to fix it — safely, step-by-step.

Claude is used for 6 distinct AI touchpoints:
  1. Fix Recommendation   — best remediation action with explanation
  2. Script Generation    — restart / rollback / cache-clear / scaling scripts
  3. Risk Assessment      — low/medium/high risk with reasoning per script
  4. Natural Language     — translate Davis's technical data for any engineer
  5. Execution Guidance   — numbered step-by-step guide with pre/post checks
  6. Resolution Validation — confirm metrics recovered after fix applied
"""

import json
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from anthropic import AsyncAnthropic
from api.config import get_settings
from api.models import (
    Incident, AIAnalysis, RemediationScript, ExecutionStep, RiskLevel
)


@lru_cache
def _get_client() -> AsyncAnthropic:
    # Reused across requests so the underlying HTTP connection pool is shared
    return AsyncAnthropic(api_key=get_settings().anthropic_api_key)


def _parse_json_response(raw: str) -> dict:
    """Parse Claude's reply, tolerating ```json fences and surrounding prose."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].removeprefix("json")
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Claude response did not contain a JSON object")
    return json.loads(raw[start:end + 1])


async def _ask_claude(prompt: str, max_tokens: int) -> dict:
    message = await _get_client().messages.create(
        model=get_settings().anthropic_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json_response(message.content[0].text)


def _build_analysis(data: dict) -> AIAnalysis:
    """Turn the recommendation JSON (live or mock) into an AIAnalysis."""
    scripts = [
        RemediationScript(
            id=str(uuid.uuid4()),
            title=s["title"],
            description=s["description"],
            language=s["language"],
            script=s["script"],
            risk_level=RiskLevel(s["risk_level"].lower()),
            risk_reason=s["risk_reason"],
            estimated_downtime=s["estimated_downtime"],
            rollback_script=s.get("rollback_script"),
        )
        for s in data.get("scripts", [])
    ]
    steps = [
        ExecutionStep(
            step_number=st["step_number"],
            title=st["title"],
            instruction=st["instruction"],
            command=st.get("command"),
            expected_outcome=st["expected_outcome"],
            is_validation=st.get("is_validation", False),
        )
        for st in data.get("execution_steps", [])
    ]
    return AIAnalysis(
        root_cause=data.get("explanation", ""),
        confidence=data.get("confidence", 80),
        impact_summary=data.get("impact_summary", ""),
        recommended_action=data.get("recommended_action", ""),
        scripts=scripts,
        execution_steps=steps,
        post_fix_checks=data.get("post_fix_checks", []),
        analysis_timestamp=datetime.now(timezone.utc),
    )


# ── Prompt builders ───────────────────────────────────────────────────────────

def _build_context(incident: Incident) -> str:
    """Build a rich context block from the Dynatrace incident for Claude."""
    entities = ", ".join(e.entity_name for e in incident.affected_entities)
    davis_rc = incident.raw_details.get("davis_root_cause") or "Not specified"
    zones = ", ".join(incident.raw_details.get("management_zones", [])) or "Default"

    return f"""
INCIDENT SUMMARY (from Dynatrace / Davis AI)
─────────────────────────────────────────────
Problem ID     : {incident.id}
Title          : {incident.title}
Type           : {incident.incident_type}
Severity       : {incident.severity}
Duration       : {incident.duration_minutes} minutes (still open)
Affected       : {entities}
Management Zone: {zones}
Davis Root Cause: {davis_rc}
Impact Level   : {incident.raw_details.get("davis_impact_level", "SERVICE")}
""".strip()


RECOMMENDATION_PROMPT = """You are a Senior SRE at a large enterprise helping customers fix production incidents.

Davis AI (Dynatrace's built-in AI) has already detected the problem and identified the root cause.
Your job is to recommend the fix and generate safe, ready-to-run scripts the customer can execute themselves.

{context}

Your response MUST be valid JSON matching this exact schema:
{{
  "recommended_action": "<one sentence: the single best fix>",
  "explanation": "<2-3 sentences explaining why this fix works and what it does>",
  "confidence": <integer 0-100>,
  "impact_summary": "<one sentence on what is currently impacted>",
  "scripts": [
    {{
      "title": "<short script title>",
      "description": "<one sentence on what this script does>",
      "language": "<bash|powershell|kubectl|python>",
      "script": "<full script with inline comments>",
      "risk_level": "<low|medium|high>",
      "risk_reason": "<one sentence explaining the risk>",
      "estimated_downtime": "<e.g. '~30s' or 'None' or '2-5 minutes'>",
      "rollback_script": "<rollback script or null if not applicable>"
    }}
  ],
  "execution_steps": [
    {{
      "step_number": <integer>,
      "title": "<short step title>",
      "instruction": "<clear instruction for this step>",
      "command": "<optional: exact command to run or null>",
      "expected_outcome": "<what should happen after this step>",
      "is_validation": <true|false>
    }}
  ],
  "post_fix_checks": [
    "<check 1: e.g. 'Confirm CPU drops below 70% in Dynatrace'>",
    "<check 2>",
    "<check 3>"
  ]
}}

Rules:
- Provide 2-4 scripts covering different approaches (e.g. restart + scale-out + cache clear)
- Scripts must be SAFE — include pre-checks, validation steps, and rollback where possible
- Include 5-8 execution steps total (mix of actions + validations)
- Mark validation steps with is_validation: true
- Scripts should be production-grade with comments explaining each section
- Always include a post-validation script that checks if the fix worked

INCIDENT TYPE GUIDANCE:
- cpu_memory     → restart service, scale out, heap dump, kill runaway process
- service_crash  → restart pod/service, check logs, rollback deployment
- db_slowness    → kill long-running queries, increase pool size, restart connection pool
- deployment_rollback → kubectl rollout undo, git revert, feature flag disable

Respond with ONLY the JSON. No markdown, no explanation outside the JSON."""


VALIDATION_PROMPT = """You are a Senior SRE reviewing whether a production incident has been resolved.

{context}

The customer has applied a remediation fix. Based on the incident details, assess whether the fix likely worked.

Respond with JSON:
{{
  "recovery_confirmed": <true|false>,
  "confidence": <integer 0-100>,
  "summary": "<2-3 sentences: what to check and whether recovery looks likely>",
  "remaining_checks": [
    "<specific Dynatrace metric or check the customer should verify>",
    "<another check>"
  ],
  "next_action": "<what to do if recovery is NOT confirmed>"
}}

Respond with ONLY the JSON."""


# ── Main AI functions ─────────────────────────────────────────────────────────

def _is_mock_mode() -> bool:
    settings = get_settings()
    key = settings.anthropic_api_key.strip()
    return settings.simulation_mode or not key or key.startswith("sk-ant-XXX") or "YOUR_ANTHROPIC" in key or "sk-ant-placeholder" in key


def _get_mock_analysis(incident: Incident) -> AIAnalysis:
    inc_type = incident.incident_type or "service_crash"

    if inc_type == "cpu_memory":
        explanation = "The web tier is suffering from severe CPU saturation on host prod-web-01. Dynatrace metrics show a single process consuming 98% of resources. Restarting the process or scaling out will immediately restore system responsiveness."
        rec_action = "Identify and terminate the runaway Node.js process using high CPU, and temporarily scale the host capacity."
        confidence = 92
        impact_summary = "Production web tier response latency has spiked to over 4.2 seconds, causing 12% of requests to timeout."

        scripts_data = [
            {
                "title": "Kill Runaway Node Process",
                "description": "Identifies and terminates the process consuming >80% CPU.",
                "language": "bash",
                "script": "#!/bin/bash\n# Pre-check: Get process ID consuming high CPU\npid=$(ps -eo pid,%cpu,cmd --sort=-%cpu | grep node | head -n 1 | awk '{print $1}')\ncpu=$(ps -p $pid -o %cpu | tail -n 1 | awk '{print int($1)}')\nif [ \"$cpu\" -gt 80 ]; then\n  echo \"Killing process $pid consuming $cpu% CPU...\"\n  kill -15 $pid\n  sleep 5\n  # Post-check\n  if kill -0 $pid 2>/dev/null; then\n    echo \"Process did not terminate gracefully, sending SIGKILL...\"\n    kill -9 $pid\n  fi\nelse\n  echo \"No runaway node process found. Top process consumes $cpu% CPU.\"\nfi",
                "risk_level": RiskLevel.MEDIUM,
                "risk_reason": "Terminating a process abruptly can abort active user sessions or operations.",
                "estimated_downtime": "None (behind load balancer)",
                "rollback_script": "echo 'Process killed. System systemd or supervisor will automatically restart it if configured.'"
            },
            {
                "title": "Scale Web Deployment (Kubernetes)",
                "description": "Scales deployment replicas to distribute load.",
                "language": "kubectl",
                "script": "# Pre-check: Verify current replica count\nkubectl get deployment web-tier -n production\n# Scale up from 2 to 4 replicas\nkubectl scale deployment web-tier -n production --replicas=4\n# Post-check: Wait for rollout\nkubectl rollout status deployment web-tier -n production",
                "risk_level": RiskLevel.LOW,
                "risk_reason": "Safe scale operation. No disruption to existing pods.",
                "estimated_downtime": "None",
                "rollback_script": "kubectl scale deployment web-tier -n production --replicas=2"
            }
        ]

        steps_data = [
            {"step_number": 1, "title": "Check CPU load", "instruction": "Check CPU load on prod-web-01 via SSH.", "command": "ssh user@prod-web-01 'uptime'", "expected_outcome": "Load average confirmed above 12.0", "is_validation": False},
            {"step_number": 2, "title": "Identify runaway process", "instruction": "Identify the process PID consuming resources.", "command": "ssh user@prod-web-01 'ps -eo pid,%cpu,cmd --sort=-%cpu | head -n 5'", "expected_outcome": "Node process shown at >90% CPU", "is_validation": False},
            {"step_number": 3, "title": "Kill runaway process", "instruction": "Run the kill process script.", "command": "./kill_runaway.sh", "expected_outcome": "Process terminated", "is_validation": False},
            {"step_number": 4, "title": "Validate CPU recovery", "instruction": "Validate CPU drop on host.", "command": "ssh user@prod-web-01 'vmstat 1 5'", "expected_outcome": "CPU idle time increases above 70%", "is_validation": True}
        ]

        checks = [
            "Verify host CPU usage drops below 60% on Dynatrace Host Dashboard.",
            "Ensure response time for web tier service stabilizes below 200ms."
        ]

    elif inc_type == "db_slowness":
        explanation = "The orders-db PostgreSQL instance is running out of available connection slots because the orders-service pool size is misconfigured, causing connection timeouts. Terminating orphan sessions will free up slots immediately."
        rec_action = "Terminate idle connection sessions and scale up the connection pool limit in orders-service."
        confidence = 89
        impact_summary = "The orders database is rejecting connections, preventing order processing and database writes."

        scripts_data = [
            {
                "title": "Kill Idle PostgreSQL Connections",
                "description": "Terminates idle backend database connections to release connection slots.",
                "language": "bash",
                "script": "# Pre-check: Count idle connections\nPGPASSWORD=$DB_PASS psql -h orders-db -U postgres -d orders -c \"SELECT count(*) FROM pg_stat_activity WHERE state = 'idle';\"\n# Terminate all connections idle for more than 5 minutes\nPGPASSWORD=$DB_PASS psql -h orders-db -U postgres -d orders -c \"\nSELECT pg_terminate_backend(pid) \nFROM pg_stat_activity \nWHERE state = 'idle' AND state_change < current_timestamp - interval '5 minutes';\"",
                "risk_level": RiskLevel.MEDIUM,
                "risk_reason": "Terminating connections can cause short-lived connection drops for active clients.",
                "estimated_downtime": "None",
                "rollback_script": "echo 'No rollback needed; clients will automatically reconnect on demand.'"
            },
            {
                "title": "Restart Connection Pool Service",
                "description": "Force restarts the orders-service application to reset all database connections.",
                "language": "kubectl",
                "script": "# Restart the deployment pods to clear pool state\nkubectl rollout restart deployment/orders-service -n production\n# Post-check: Wait for running pods\nkubectl rollout status deployment/orders-service -n production",
                "risk_level": RiskLevel.MEDIUM,
                "risk_reason": "Forces connection closures, pods will re-initialize pool on start.",
                "estimated_downtime": "None",
                "rollback_script": "echo 'Cannot rollback a restart, service is rolling.'"
            }
        ]

        steps_data = [
            {"step_number": 1, "title": "Query database connection limits", "instruction": "Query database connection limits.", "command": "psql -h orders-db -U postgres -c 'show max_connections;'", "expected_outcome": "Max connections set to 100", "is_validation": False},
            {"step_number": 2, "title": "Check active database session count", "instruction": "Check active database session count.", "command": "psql -h orders-db -U postgres -c 'select count(*) from pg_stat_activity;'", "expected_outcome": "Active connections near max (e.g. 98)", "is_validation": False},
            {"step_number": 3, "title": "Execute termination script", "instruction": "Execute the idle connection termination script.", "command": "./kill_idle.sh", "expected_outcome": "Terminated 42 idle sessions", "is_validation": False},
            {"step_number": 4, "title": "Validate DB is responding", "instruction": "Validate database is responding.", "command": "pg_isready -h orders-db -p 5432", "expected_outcome": "Database accepts connections", "is_validation": True}
        ]

        checks = [
            "Monitor connection count on Postgres dashboard in Dynatrace.",
            "Ensure order submission rate climbs back to baseline."
        ]

    elif inc_type == "deployment_rollback":
        explanation = "A sudden 5% HTTP 500 error rate spike was detected directly following the deployment of tag v2.4.1. The errors originate from a new user recommendation API path. Disabling the feature flag will immediately stop requests to this endpoint."
        rec_action = "Disable the new v2.4.1 feature flag or perform a deployment rollback to stable version v2.4.0."
        confidence = 95
        impact_summary = "Users are experiencing errors when loading their profiles, with the HTTP 500 error rate peaking at 12%."

        scripts_data = [
            {
                "title": "Disable Feature Flag via API",
                "description": "Disables the user-recommendation feature flag to bypass buggy code path.",
                "language": "bash",
                "script": "# Pre-check: Fetch current flag status\ncurl -s -H \"Authorization: Bearer $FLAG_API_KEY\" https://flags.production.internal/api/v1/flags/user-rec\n# Disable the flag\ncurl -s -X PATCH -H \"Authorization: Bearer $FLAG_API_KEY\" \\\n  -H \"Content-Type: application/json\" \\\n  -d '{\"enabled\": false}' \\\n  https://flags.production.internal/api/v1/flags/user-rec/toggle\n# Post-check\ncurl -s -H \"Authorization: Bearer $FLAG_API_KEY\" https://flags.production.internal/api/v1/flags/user-rec",
                "risk_level": RiskLevel.LOW,
                "risk_reason": "Safe feature flag toggle; dynamic change does not require server restarts.",
                "estimated_downtime": "None",
                "rollback_script": "curl -s -X PATCH -H \"Authorization: Bearer $FLAG_API_KEY\" -H \"Content-Type: application/json\" -d '{\"enabled\": true}' https://flags.production.internal/api/v1/flags/user-rec/toggle"
            },
            {
                "title": "Rollback User API Service",
                "description": "Performs a git revert or redeploys user-api to tag v2.4.0.",
                "language": "kubectl",
                "script": "# Set deployment image back to the previous stable release tag\nkubectl set image deployment/user-api user-api=registry.internal/user-api:v2.4.0 -n production\n# Post-check: Monitor rolling restart progress\nkubectl rollout status deployment/user-api -n production",
                "risk_level": RiskLevel.MEDIUM,
                "risk_reason": "Safe rollback, but requires pulling the previous docker image and container replacement.",
                "estimated_downtime": "None",
                "rollback_script": "kubectl set image deployment/user-api user-api=registry.internal/user-api:v2.4.1 -n production"
            }
        ]

        steps_data = [
            {"step_number": 1, "title": "Check errors in logs", "instruction": "Fetch HTTP error metrics from logs.", "command": "kubectl logs -n production -l app=user-api --tail=100 | grep '500 Internal'", "expected_outcome": "Multiple Sentry error traces logged", "is_validation": False},
            {"step_number": 2, "title": "Disable the feature flag", "instruction": "Disable the recommendation feature flag.", "command": "./toggle_flag.sh", "expected_outcome": "Flag 'user-rec' disabled", "is_validation": False},
            {"step_number": 3, "title": "Validate endpoint health", "instruction": "Validate error rate reduction.", "command": "curl -s https://user-api.production.internal/health", "expected_outcome": "Health status returns OK", "is_validation": True}
        ]

        checks = [
            "Ensure HTTP 500 error count drops to zero in Dynatrace dashboard.",
            "Verify user profile page load times return to normal."
        ]

    else:  # service_crash
        explanation = "The payment-service pods are crashing immediately upon startup due to a database migration mismatch in version v2.3.9. Rolling back the deployment will restore payment processing immediately while the code fix is prepared."
        rec_action = "Perform a rollout rollback to the previous stable image tag (v2.3.8) and check application crash logs."
        confidence = 98
        impact_summary = "The checkout flow is broken, and customers are unable to complete purchases. Checkout API is returning 500 Internal Server Errors."

        scripts_data = [
            {
                "title": "Rollback Payment Service Deployment",
                "description": "Rolls back payment-service deployment in Kubernetes to the previous revision.",
                "language": "kubectl",
                "script": "# Pre-check: Check rollout history\nkubectl rollout history deployment/payment-service -n production\n# Rollback to previous deployment revision\nkubectl rollout undo deployment/payment-service -n production\n# Post-check: Monitor deployment status\nkubectl rollout status deployment/payment-service -n production",
                "risk_level": RiskLevel.LOW,
                "risk_reason": "Safe rollback operation returning to a known working state.",
                "estimated_downtime": "None (zero-downtime rolling update)",
                "rollback_script": "kubectl rollout undo deployment/payment-service -n production --to-revision=0"
            },
            {
                "title": "Fetch Pod Diagnostics and Restart",
                "description": "Restarts the payment-service deployment to clear transient lockups.",
                "language": "kubectl",
                "script": "# Pre-check: Print crash logs\nkubectl logs -l app=payment-service -n production --tail=100 --previous\n# Restart the rollout\nkubectl rollout restart deployment/payment-service -n production\n# Post-check: Wait for restart\nkubectl rollout status deployment/payment-service -n production",
                "risk_level": RiskLevel.MEDIUM,
                "risk_reason": "If the pod is crashlooping due to an image bug, restarting will not fix it and may cause transient capacity reduction.",
                "estimated_downtime": "None",
                "rollback_script": "echo 'Restart completed.'"
            }
        ]

        steps_data = [
            {"step_number": 1, "title": "Check pod status", "instruction": "Check current pod status in the namespace.", "command": "kubectl get pods -n production -l app=payment-service", "expected_outcome": "Pods show status CrashLoopBackOff", "is_validation": False},
            {"step_number": 2, "title": "Retrieve logs", "instruction": "Retrieve logs from the failed pod.", "command": "kubectl logs -n production -l app=payment-service --tail=50", "expected_outcome": "DB connection error or stack trace shown", "is_validation": False},
            {"step_number": 3, "title": "Rollback deployment", "instruction": "Trigger the deployment rollback.", "command": "./rollback_payment.sh", "expected_outcome": "Rollback triggered successfully", "is_validation": False},
            {"step_number": 4, "title": "Validate pod states", "instruction": "Validate that the new pods are running successfully.", "command": "kubectl get pods -n production -l app=payment-service -w --timeout=30s", "expected_outcome": "Pods reach 'Running' status and pass readiness probes", "is_validation": True}
        ]

        checks = [
            "Ensure payment-service pod status stays 'Running' for > 5 minutes.",
            "Confirm API gateway success rate for /checkout endpoints returns to 100%."
        ]

    return _build_analysis({
        "explanation": explanation,
        "confidence": confidence,
        "impact_summary": impact_summary,
        "recommended_action": rec_action,
        "scripts": scripts_data,
        "execution_steps": steps_data,
        "post_fix_checks": checks,
    })


def _get_mock_validation(incident: Incident) -> dict:
    inc_type = incident.incident_type or "service_crash"
    if inc_type == "cpu_memory":
        return {
            "recovery_confirmed": True,
            "confidence": 95,
            "summary": "Host CPU saturation has subsided. The top consuming processes are now running under normal thresholds (idle time has returned to 78%).",
            "remaining_checks": [
                "Monitor memory saturation to ensure there is no secondary leak",
                "Verify that background worker jobs resume successfully"
            ],
            "next_action": "No immediate action required. System is stable."
        }
    elif inc_type == "db_slowness":
        return {
            "recovery_confirmed": True,
            "confidence": 90,
            "summary": "PG backend sessions terminated successfully. Active connections have fallen from 98/100 to 36/100, which is well within capacity.",
            "remaining_checks": [
                "Monitor connection usage over peak hours to ensure pool doesn't fill up again",
                "Check database lock logs to verify no transactions are lingering"
            ],
            "next_action": "Adjust connection pool maximum limit in application configurations to matching values."
        }
    elif inc_type == "deployment_rollback":
        return {
            "recovery_confirmed": True,
            "confidence": 95,
            "summary": "Feature flag 'user-rec' has been disabled. The user-api HTTP 500 errors dropped to zero immediately, confirming the buggy code path was bypassed.",
            "remaining_checks": [
                "Monitor user profile loading times",
                "Verify that user dashboard runs fine with the fallback profile renderer"
            ],
            "next_action": "Hotfix recommended for user recommendation API path before re-enabling the feature flag."
        }
    else: # service_crash
        return {
            "recovery_confirmed": True,
            "confidence": 98,
            "summary": "Rollback was successful. Pod status shows 'Running' and container readiness probes are passing. CrashLoopBackOff state has ended.",
            "remaining_checks": [
                "Check error rate metrics on checkout-api to verify it can reach payment-service",
                "Confirm that transaction logs show successful operations"
            ],
            "next_action": "Investigate tag v2.3.9 container startup logs in the staging cluster to debug the database schema mismatch."
        }


async def analyze_incident(incident: Incident) -> AIAnalysis:
    """
    🤖 AI TOUCHPOINTS 1, 2, 3, 4, 5
    Given a Dynatrace incident (with Davis AI root cause baked in),
    Claude produces:
      - A fix recommendation with plain-English explanation
      - 2-4 ready-to-run remediation scripts (restart/rollback/cache/scale)
      - Risk assessment per script
      - Step-by-step execution guide
      - Post-fix validation checklist
    """
    if _is_mock_mode():
        return _get_mock_analysis(incident)

    prompt = RECOMMENDATION_PROMPT.format(context=_build_context(incident))
    return _build_analysis(await _ask_claude(prompt, max_tokens=4096))


async def validate_resolution(incident: Incident) -> dict:
    """
    🤖 AI TOUCHPOINT 6
    After the customer applies a fix, Claude reviews the incident context
    and confirms whether recovery metrics indicate the issue is resolved.
    """
    if _is_mock_mode():
        return _get_mock_validation(incident)

    prompt = VALIDATION_PROMPT.format(context=_build_context(incident))
    return await _ask_claude(prompt, max_tokens=1024)
