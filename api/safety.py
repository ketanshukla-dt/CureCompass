"""Guardrails for AI-generated remediation scripts."""

import re

_RISKY_SCRIPT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\brm\s+-[a-z]*r[a-z]*f|\brm\s+-[a-z]*f[a-z]*r",   # rm -rf
        r"(curl|wget)[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh",       # curl | sh
        r"\bdrop\s+(table|database)\b|\btruncate\s+table\b",
        r"\bmkfs\b|\bdd\s+if=.*of=/dev/",
        r"remove-item[^\n]*-recurse[^\n]*-force",
        r"--force\b|--grace-period=0",
        r"chmod\s+-R\s+777",
        r"iptables\s+-F|ufw\s+disable|setenforce\s+0",
    )
]

RISK_FLAG_PREFIX = "[Auto-flagged: contains potentially destructive commands]"
ROLLBACK_FLAG_PREFIX = "[Auto-flagged: rollback script contains potentially destructive commands]"


def is_risky_script(script: str) -> bool:
    """True if the script contains a command from the destructive-command deny-list."""
    return any(pattern.search(script) for pattern in _RISKY_SCRIPT_PATTERNS)
