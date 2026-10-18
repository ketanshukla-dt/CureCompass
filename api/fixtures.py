"""Canned demo output used when SIMULATION_MODE=true (no LLM call is made)."""

from api.analysis import build_analysis
from api.models import AIAnalysis, Incident, RiskLevel


def mock_analysis(incident: Incident) -> AIAnalysis:
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
                "title": "Gracefully Restart Web Service",
                "description": "Restarts the web service on the affected host after draining traffic.",
                "language": "bash",
                "script": "#!/bin/bash\n# Assumes a systemd-managed web service. Replace <WEB_SERVICE> with your unit name.\nHOST=prod-web-01\n# Pre-check: confirm the service state and current load\nssh user@$HOST 'systemctl status <WEB_SERVICE> --no-pager | head -n 5; uptime'\n# Drain this host from the load balancer first using your LB tooling, then restart\nssh user@$HOST 'sudo systemctl restart <WEB_SERVICE>'\n# Post-check: confirm the service is active and CPU has dropped\nssh user@$HOST 'systemctl is-active <WEB_SERVICE>; vmstat 1 3'",
                "risk_level": RiskLevel.MEDIUM,
                "risk_reason": "A restart drops in-flight requests on this host unless it is drained first.",
                "estimated_downtime": "~10-30s on this host (none if drained)",
                "rollback_script": "ssh user@prod-web-01 'sudo systemctl start <WEB_SERVICE>'"
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
                "description": "Restarts the orders-service application to reset all database connections.",
                "language": "bash",
                "script": "#!/bin/bash\n# Assumes a systemd-managed service. Replace <APP_HOST> with the orders-service host.\n# Pre-check: confirm the service is running\nssh user@<APP_HOST> 'systemctl status orders-service --no-pager | head -n 5'\n# Restart so the connection pool is rebuilt from scratch\nssh user@<APP_HOST> 'sudo systemctl restart orders-service'\n# Post-check: confirm it is active again\nssh user@<APP_HOST> 'systemctl is-active orders-service'",
                "risk_level": RiskLevel.MEDIUM,
                "risk_reason": "Restart closes all existing database connections; the pool is rebuilt on start.",
                "estimated_downtime": "~10-30s for orders-service",
                "rollback_script": "ssh user@<APP_HOST> 'sudo systemctl start orders-service'"
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
                "description": "Redeploys user-api at the previous stable release (v2.4.0).",
                "language": "bash",
                "script": "#!/bin/bash\n# Uses your existing release tooling. Replace <DEPLOY_CMD> with it\n# (CI/CD pipeline trigger, deploy script, package manager, etc.).\n# Pre-check: confirm the version currently running\ncurl -s https://user-api.production.internal/version\n# Redeploy the previous stable release\n<DEPLOY_CMD> --service user-api --version v2.4.0\n# Post-check: confirm the rolled-back version is live and healthy\ncurl -s https://user-api.production.internal/version\ncurl -s https://user-api.production.internal/health",
                "risk_level": RiskLevel.MEDIUM,
                "risk_reason": "A rollback replaces the running release; verify v2.4.0 is compatible with current data.",
                "estimated_downtime": "Depends on your deployment method",
                "rollback_script": "<DEPLOY_CMD> --service user-api --version v2.4.1"
            }
        ]

        steps_data = [
            {"step_number": 1, "title": "Check errors in logs", "instruction": "Fetch HTTP error metrics from logs.", "command": "ssh user@<APP_HOST> \"grep ' 500 ' /var/log/user-api/access.log | tail -n 20\"", "expected_outcome": "Recent HTTP 500 responses on the recommendation path", "is_validation": False},
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
        # Kubernetes commands are appropriate here: the incident itself reports crash-looping pods.
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

    return build_analysis({
        "explanation": explanation,
        "confidence": confidence,
        "impact_summary": impact_summary,
        "recommended_action": rec_action,
        "scripts": scripts_data,
        "execution_steps": steps_data,
        "post_fix_checks": checks,
    })


def mock_validation(incident: Incident) -> dict:
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
