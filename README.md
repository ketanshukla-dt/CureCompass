# 🔧 CureCompass — Intelligent Incident Remediation Platform
> **Dynatrace AI Innovation Contest**

**Davis AI detects the problem. Claude prescribes the cure. You stay in control.**

---

## 🎯 The Problem We're Solving

Operations teams waste hours manually investigating incidents — they know *something* is broken, but not exactly what caused it or how to fix it safely. Every remediation is manual, error-prone, and time-consuming. Customers want automation but can't allow third-party access to production servers.

**The gap:** There's no intelligence layer that tells customers *exactly* what went wrong and *how to fix it safely*.

---

## 💡 Our Solution

CureCompass is an AI-powered remediation guidance platform that sits on top of Dynatrace. When an incident fires:

1. **Davis AI** detects the problem and identifies the root cause (via Dynatrace Problems API)
2. **Claude (Anthropic)** reads Davis's diagnosis and recommends the best fix — in plain English
3. **Claude generates safe, ready-to-run scripts** — restart, rollback, cache clear, scale-out
4. **Claude writes step-by-step execution guidance** with pre/post validation checks
5. **Claude validates recovery** — confirms whether metrics show the incident is resolved
6. **Customers stay in control** — they decide what runs in their environment

---

## 🤖 Where AI Is Used (6 Touchpoints)

| # | AI Touchpoint | What Claude Does |
|---|---|---|
| 1 | **Fix Recommendation** | Reads Davis AI's root cause → recommends the best remediation action with explanation |
| 2 | **Script Generation** | Generates safe, production-grade Bash/kubectl/PowerShell scripts for the exact incident |
| 3 | **Risk Assessment** | Labels each script `low` / `medium` / `high` risk with a clear reason |
| 4 | **NL Translation** | Converts dense Dynatrace technical payloads into plain English any engineer can act on |
| 5 | **Execution Guidance** | Writes numbered step-by-step instructions with exact commands, pre-checks, expected outcomes |
| 6 | **Resolution Validation** | After the fix is applied, confirms whether metrics indicate successful recovery |

> **Davis AI + Claude = Detection + Remediation.** Davis knows what broke. Claude knows how to fix it.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│              Dynatrace (Davis AI)                    │
│    Problems API v2 → Root Cause + Affected Entities  │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│               CureCompass Backend                    │
│  ┌──────────────┐    ┌────────────────────────────┐ │
│  │ dynatrace.py │    │      ai_engine.py           │ │
│  │ Fetch + parse│───▶│  Claude: Recommend + Script │ │
│  │ Davis data   │    │  + Risk + Guide + Validate  │ │
│  └──────────────┘    └────────────────────────────┘ │
│          FastAPI REST API + SQLite History           │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│            React Frontend (Tailwind)                 │
│  Dashboard → Incident Detail → Scripts → Guide       │
│  → Mark Outcome → Validate Recovery → History        │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Dynatrace tenant + API token *(Problems v2 Read + Entities Read scopes)*
- Anthropic API key

### Setup & Run

```bash
# 1. Clone the repo
git clone https://github.com/ketanshukla-dt/CureCompass.git
cd CureCompass

# 2. Configure credentials
cp .env.example .env
# Edit .env — add your DT_TENANT_URL, DT_API_TOKEN, ANTHROPIC_API_KEY

# 3. One-command start (installs deps + builds frontend + starts server)
./start.sh

# 4. Open http://localhost:8000
```

### Windows
If you are testing on Windows, run the PowerShell startup script instead:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
./start.ps1
```

This script uses Python 3.12 or 3.11 via `py.exe` if installed, otherwise the `python` on your PATH (3.11+ required).

If you are using Python 3.14 and see a dependency build error for `pydantic-core`, switch to Python 3.11 or 3.12 and retry, or install Visual Studio Build Tools with the C++ toolchain.

> **No Dynatrace tenant?** Set `SIMULATION_MODE=true` in `.env` — the platform runs with realistic mock incidents covering all 4 incident types.

---

## ⚙️ Environment Variables

| Variable | Description |
|---|---|
| `DT_TENANT_URL` | Your Dynatrace SaaS tenant URL (e.g. `https://abc123.live.dynatrace.com`) |
| `DT_API_TOKEN` | API token with `problems.read` + `entities.read` scopes |
| `ANTHROPIC_API_KEY` | Claude API key from [console.anthropic.com](https://console.anthropic.com) |
| `SIMULATION_MODE` | `true` = use mock incidents (default: `false`) |
| `PORT` | Server port (default: `8000`) |
| `HOST` | Interface to bind (default: `127.0.0.1`; the app has no login, so only widen behind an authenticating proxy) |
| `ANTHROPIC_MODEL` | Claude model to use (default: `claude-sonnet-5-5`) |
| `CORS_ORIGINS` | Extra allowed browser origins, comma-separated (only needed for the Vite dev server) |

---

## 📄 License

Copyright (c) 2026 Ketan Shukla. All rights reserved. See [LICENSE](LICENSE).

---

## 📂 Project Structure

```
CureCompass/
├── main.py                    # FastAPI monolith entry point
├── requirements.txt
├── start.sh                   # One-command start script
├── build.sh                   # Rebuild frontend only
├── .env.example
│
├── api/
│   ├── config.py              # Settings (env vars)
│   ├── models.py              # Pydantic data models
│   ├── database.py            # SQLite: history + analysis cache
│   ├── dynatrace.py           # Dynatrace Problems API + simulation mode
│   └── ai_engine.py           # 🤖 Claude integration (all 6 AI touchpoints)
│
├── routes/
│   ├── incidents.py           # GET/POST /api/incidents
│   └── history.py             # GET /api/history
│
└── frontend/                  # React + Vite + Tailwind
    └── src/
        ├── pages/
        │   ├── Dashboard.jsx       # Incident feed
        │   ├── IncidentDetail.jsx  # AI analysis + scripts + guide
        │   └── History.jsx         # Remediation history + stats
        └── components/
            ├── ScriptViewer.jsx    # Syntax-highlighted scripts + copy/download
            └── StepGuide.jsx       # Interactive step-by-step guide
```

---

## 🎬 Demo Walkthrough

1. **Open the dashboard** — see active incidents pulled from Dynatrace, sorted by severity
2. **Click a Critical incident** — view Davis AI's root cause data
3. **Click "Analyze with AI"** — Claude analyzes the incident and generates remediation options
4. **Switch to Scripts tab** — see 2–4 ready-to-run scripts with risk labels and rollback options
5. **Open Execution Guide** — follow the step-by-step checklist, copy exact commands
6. **Mark the outcome** — record whether the fix worked
7. **Validate Recovery** — Claude confirms if metrics show the incident is resolved
8. **Check History** — view all past remediations, success rate, avg resolution time

---

## 🛠️ Incident Types Covered

| Type | Example | Remediation Scripts |
|---|---|---|
| ⚡ CPU / Memory | Host resource saturation | Kill runaway process, scale out, heap dump |
| 💥 Service Crash | Pod crashlooping | Restart pod, check logs, rollback deployment |
| 🗄️ Database | Connection pool exhaustion | Kill long queries, increase pool, restart connections |
| 🔄 Deployment | Error rate spike after deploy | `kubectl rollout undo`, git revert, feature flag disable |

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **AI** | Claude (default `claude-sonnet-5-5`, configurable via `ANTHROPIC_MODEL`) via Anthropic Python SDK |
| **Monitoring** | Dynatrace Problems API v2 + Davis AI |
| **Backend** | Python · FastAPI · aiosqlite |
| **Frontend** | React 18 · Vite · Tailwind CSS |
| **Deployment** | Single Python process (monolith) |

---

*Powered by [Dynatrace Davis AI](https://www.dynatrace.com/platform/artificial-intelligence/) + [Anthropic Claude](https://www.anthropic.com)*
