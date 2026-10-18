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
│  │ dynatrace.py │    │  ai_engine.py + prompts.py  │ │
│  │ Fetch, parse │───▶│  Recommend + Script + Risk  │ │
│  │ + classify   │    │  + Guide + Validate         │ │
│  └──────────────┘    └──────┬──────────────┬──────┘ │
│                             │              │        │
│                   ┌─────────▼──────┐ ┌─────▼──────┐ │
│                   │ llm/ provider  │ │ analysis + │ │
│                   │ anthropic |    │ │ safety.py  │ │
│                   │ bedrock |      │ │ validate + │ │
│                   │ vertex |ollama │ │ flag risky │ │
│                   └────────────────┘ └────────────┘ │
│     FastAPI REST API + SQLite (history + cache)      │
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

> **No Dynatrace tenant?** Set `SIMULATION_MODE=true` in `.env` — the platform runs with realistic mock incidents covering all 5 incident types.

---

## ⚙️ Environment Variables

| Variable | Description |
|---|---|
| `DT_TENANT_URL` | Your Dynatrace SaaS tenant URL (e.g. `https://abc123.live.dynatrace.com`) |
| `DT_API_TOKEN` | API token with `problems.read` + `entities.read` scopes |
| `LLM_PROVIDER` | `anthropic` (default), `bedrock`, `vertex` or `ollama` — see [LLM providers](#-llm-providers) |
| `ANTHROPIC_API_KEY` | Claude API key (only for `LLM_PROVIDER=anthropic`) |
| `ANTHROPIC_MODEL` | Model id for the chosen provider (default: `claude-sonnet-5-5`) |
| `SIMULATION_MODE` | `true` = mock incidents + canned AI output, no keys needed (default: `false`) |
| `PORT` | Server port (default: `8000`) |
| `HOST` | Interface to bind (default: `127.0.0.1`; the app has no login, so only widen behind an authenticating proxy) |
| `CORS_ORIGINS` | Extra allowed browser origins, comma-separated (only needed for the Vite dev server) |
| `DATABASE_PATH` | SQLite file (default: `incidents.db`, relative to the project root) |
| `ANALYSIS_CACHE_TTL_MINUTES` | How long a cached AI analysis is reused (default: `1440`) |

Provider-specific settings (`AWS_REGION`, `VERTEX_PROJECT_ID`, `VERTEX_REGION`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`) are listed in `.env.example`.

---

## 🔌 LLM Providers

The AI layer is provider-neutral. Choose a backend with `LLM_PROVIDER`:

| Provider | Credentials | Extra install |
|---|---|---|
| `anthropic` | `ANTHROPIC_API_KEY` | none |
| `bedrock` | Standard AWS credential chain | `pip install "anthropic[bedrock]"` |
| `vertex` | `gcloud auth application-default login` + `VERTEX_PROJECT_ID` | `pip install "anthropic[vertex]"` |
| `ollama` | none (local model) | Ollama running locally |

With no provider access at all, set `SIMULATION_MODE=true`. Incident data can contain hostnames and comments from your tenant — only use providers your organisation has approved.

---

## 🛡️ Safety & Security

CureCompass only *advises* — it never executes anything against your environment.

- **Destructive-script flagging** — generated scripts are scanned against a deny-list (`rm -rf`, `curl | sh`, `DROP TABLE`, `--force`, `iptables -F`, ...); matches are auto-flagged as high risk in the UI.
- **Prompt-injection defences** — incident data is sanitised and passed to the model as tagged data under a fixed system prompt.
- **Validated output** — model JSON is parsed into typed Pydantic models before it reaches the UI.
- **Secure defaults** — binds to `127.0.0.1`, restricted CORS, incident-ID validation, no internal error details returned to clients.
- **Reliability** — AI analyses are cached (with TTL) and de-duplicated per incident; LLM calls use timeouts and retries; `/healthz` for liveness checks.

---

## 🔗 API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/incidents` | List active incidents |
| `GET` | `/api/incidents/{id}` | Incident detail (with cached analysis, if any) |
| `POST` | `/api/incidents/{id}/analyze` | Run the AI analysis (cache-aware; `force` re-runs) |
| `POST` | `/api/incidents/{id}/resolve` | Record the outcome: `success` / `partial` / `failed` |
| `POST` | `/api/incidents/{id}/validate` | AI check of whether recovery is confirmed |
| `GET` | `/api/history` | Remediation history |
| `GET` | `/api/history/stats` | Success rate and average resolution time |
| `GET` | `/healthz` | Health check |

---

## 🧪 Development

```bash
pip install -r requirements-dev.txt
pytest          # backend tests (run in simulation mode, no keys needed)
ruff check .    # lint
```

CI (`.github/workflows/ci.yml`) runs lint, tests and the frontend build on every push and pull request. See [docs/ROADMAP.md](docs/ROADMAP.md) for where the project is heading.

---

## 📂 Project Structure

```
CureCompass/
├── main.py                    # FastAPI monolith entry point (+ /healthz)
├── requirements.txt           # Runtime dependencies
├── requirements-dev.txt       # + pytest, ruff
├── pyproject.toml             # pytest + ruff config
├── start.sh / start.ps1       # One-command start scripts
├── build.sh                   # Rebuild frontend only
├── .env.example
│
├── api/
│   ├── config.py              # Settings (env vars)
│   ├── models.py              # Pydantic data models
│   ├── database.py            # SQLite: history + analysis cache (with TTL)
│   ├── dynatrace.py           # Dynatrace Problems API + simulation incidents
│   ├── ai_engine.py           # 🤖 Orchestrates the 6 AI touchpoints
│   ├── prompts.py             # Prompt text + sanitised incident context
│   ├── analysis.py            # LLM JSON -> validated models
│   ├── safety.py              # Destructive-command deny-list for scripts
│   ├── fixtures.py            # Canned output for SIMULATION_MODE
│   └── llm/                   # Provider layer: anthropic | bedrock | vertex | ollama
│
├── routes/
│   ├── incidents.py           # GET/POST /api/incidents
│   └── history.py             # GET /api/history
│
├── tests/                     # pytest suite (runs without any keys)
├── docs/ROADMAP.md            # Phased roadmap
├── .github/workflows/ci.yml   # Lint + tests + frontend build
│
└── frontend/                  # React + Vite + Tailwind
    └── src/
        ├── pages/             # Dashboard, IncidentDetail (+ incident/ parts), History
        ├── components/        # IncidentCard, ScriptViewer, StepGuide, ...
        └── utils/             # errors.js, format.js
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
| 📡 Monitoring Gap | ActiveGate, OneAgent, extension or synthetic-location outage (not an app failure) | Check monitoring component health and connectivity instead of treating it as an app incident |

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **AI** | Claude (default `claude-sonnet-5-5`, configurable via `ANTHROPIC_MODEL`) via the Anthropic Python SDK — direct API, Amazon Bedrock or Google Vertex AI; or a local model via Ollama |
| **Monitoring** | Dynatrace Problems API v2 + Davis AI |
| **Backend** | Python 3.11+ · FastAPI · aiosqlite · Pydantic v2 |
| **Frontend** | React 18 · Vite · Tailwind CSS |
| **Quality** | pytest · ruff · GitHub Actions CI |
| **Deployment** | Single Python process (monolith) |

---

## 📄 License

Copyright (c) 2026 Ketan Shukla. All rights reserved. See [LICENSE](LICENSE).

---

*Powered by [Dynatrace Davis AI](https://www.dynatrace.com/platform/artificial-intelligence/) + [Anthropic Claude](https://www.anthropic.com)*
