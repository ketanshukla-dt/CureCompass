# CureCompass Roadmap

**Vision:** Davis AI detects the problem. An LLM prescribes the cure. The customer stays in control.

CureCompass starts as a standalone prototype and is designed to move into a Dynatrace
tenant as a customer-facing capability, guided by Product Management and R&D.

## Phase overview

| Phase | Goal | Status |
|---|---|---|
| 0. Prototype | End-to-end flow: incidents, AI analysis, scripts, guide, history | Done |
| 1. Foundation | Secure, tested, provider-neutral codebase | **Done** (this release) |
| 2. Pilot-ready | Real tenant data, auth, observability, evaluation | Next |
| 3. Product alignment | Fit into the Dynatrace platform with PM and R&D | Planned |
| 4. Customer value | Wider use cases and closed-loop learning | Planned |

---

## Phase 0 — Prototype (done)

- Dynatrace Problems v2 integration with simulation mode for offline demos
- Six AI touchpoints: recommendation, scripts, risk, plain-English, execution guide, validation
- React UI: dashboard, incident detail, script viewer, step guide, history and stats

## Phase 1 — Foundation (done)

| Area | Delivered |
|---|---|
| Security | Loopback bind by default, restricted CORS, prompt-injection defences (system prompt, tagged and sanitised data), destructive-script auto-flagging (main script, rollback script and step commands), incident-ID validation, no error leakage |
| Provider layer | `LLM_PROVIDER` = anthropic, bedrock, vertex or ollama behind one interface; clear 503 when unconfigured |
| Code quality | `ai_engine.py` split into `prompts`, `analysis`, `safety`, `fixtures`, `llm/`; typed models with validation; word-boundary incident classification |
| Reliability | Cache-aware `/analyze` with per-incident dedupe, cache TTL, `force` re-run, timeouts and retries, `/healthz` |
| Quality gates | pytest suite (no keys needed), ruff, GitHub Actions CI |
| Frontend | Error and retry states, stale-response guard, resolve confirmation, safe downloads, accessibility, smaller components |
| Hygiene | One product name, LICENSE (proprietary), docs, clean `.gitignore` |

## Phase 2 — Pilot-ready (next, 2-4 weeks)

**Goal:** a team can use it against a real tenant, safely.

1. **Approved model access.** Obtain Dynatrace-approved API access (for example Bedrock or Vertex) via the Claude deployment leads; replace personal keys.
2. **Authentication.** Put the app behind SSO or a reverse proxy; add per-user identity to history (who ran or resolved what).
3. **Observability.** OpenTelemetry traces and metrics to Dynatrace: spans around every LLM call with model, latency and token usage; structured logs with request IDs.
4. **Evaluation harness.** A curated set of incidents with expected outcomes; score each model on JSON validity, script safety and usefulness. This is the evidence R&D will ask for.
5. **Structured output.** Move from "reply with JSON" to the provider's tool-use or schema mode; retry once on validation failure.
6. **Audit log.** Immutable record of analyses generated and scripts copied or downloaded.
7. **Rate limiting and cost guardrails.** Per-user limits and token budgets.

**Exit criteria:** runs on a real tenant for a pilot team; evaluation scores recorded; no personal keys; authenticated access.

## Phase 3 — Product alignment (with PM and R&D)

**Decisions to take together:**

| Question | Why it matters |
|---|---|
| Which model hosting is approved for customer data? | Data residency, contracts, cost |
| Build on existing Dynatrace AI services or call a model directly? | Reuse vs control |
| Standalone web app or a Dynatrace App (AppEngine)? | Authentication, packaging, distribution |
| Who owns token cost: Dynatrace or the customer? | Pricing and quotas |
| What may be sent to a model? | Hostnames, comments and entity names can be sensitive |

### Suggestions from Product Management

Three suggestions were made for how CureCompass should be implemented for Dynatrace customers. They are sequenced so that the contained change comes first and the larger ones are evaluated before any rebuild.

| Step | Suggestion | Type of work | Outcome |
|---|---|---|---|
| 3A | Use the DQL-based Storage query API instead of Problems API v2 | Implementation | Richer data for the model; recovery validated from metrics |
| 3B | Look into the Dynatrace Remote MCP server | Evaluation, then optional implementation | Decision on letting the model fetch context itself |
| 3C | Check whether a Dynatrace App is more efficient for customers | Evaluation, then decision | Go or no-go on app-based delivery |

**3A. DQL Storage query API.** Replace or supplement the live path in `api/dynatrace.py`; the `Incident` model, routes, prompts and UI stay as they are.
- Customer value: the model sees logs, metrics and events around the problem, not only evidence names and comments; recovery validation becomes measurable (today `/validate` re-reads the problem and asks the model; it does not query metrics); the 100-problem, open-only limit of the list call can be tuned.
- Work: DQL queries per incident type; keep Problems v2 behind a feature flag until parity; extend `build_context` within the existing field limits and sanitising; add a metric-based validation path; document the token scopes; re-run the evaluation set.
- Risks: DQL queries are billed by data scanned (use short windows, targeted queries, caching and a query budget); different token scopes; more context means more potentially sensitive data sent to the model.
- Exit: parity with Problems v2 on all five incident types and better scores on the evaluation set.

**3B. Dynatrace Remote MCP server.** Evaluate letting the model call Dynatrace tools (including DQL) itself instead of receiving one fixed payload.
- Questions: which tools are exposed; which environments are supported (third-party listings suggest Dynatrace Managed and classic live URLs may not be, to be confirmed in official docs); authentication and read-only scoping; predictability, cost and latency when the model chooses its own queries; how to keep it testable in the evaluation harness.
- Approach: proof of concept through the existing provider layer on the five incident types plus two unfamiliar ones; compare with 3A; write a one-page recommendation (primary, optional mode, or defer).

**3C. Dynatrace App (AppEngine).** Evaluate delivery inside the customer's tenant with the Dynatrace App Toolkit and design system.
- Customer value: no second tool or login; no server to host or patch; platform authentication and distribution.
- Carry-over: the Python prompts, deny-list, parsing and provider layer would need porting to TypeScript or hosting as an external service called from an app function; the React pages would be rebuilt; SQLite would be replaced by tenant-backed storage; where the model API key lives and how outbound model calls are approved must be checked with the platform team.
- Approach: a thin vertical slice (an app page that lists problems through DQL and shows one model-generated recommendation), then score standalone versus app on adoption effort, security review effort, development effort, feature fit and ownership.

**Work after the decisions:** port the UI to the platform's app framework (if 3C is go), replace SQLite with tenant-backed storage, replace the API token with tenant authentication, security and privacy review, legal sign-off before any public release.

## Phase 4 — Customer value

- **Wider incident coverage:** Kubernetes, cloud services, network, security, and monitoring-infrastructure problems (ActiveGate, synthetic locations, OneAgent).
- **Closed loop:** feed remediation outcomes back to Dynatrace as events; learn which fixes work per environment.
- **Runbook integration:** emit approved fixes to workflow and automation tooling instead of copy-and-paste, always with a human approval step.
- **Retrieval:** ground recommendations in the customer's own runbooks and past incidents.
- **Streaming UI:** stream analysis as it is generated.
- **Multi-tenant and roles:** read-only versus approver roles.

## Principles

1. **Human in the loop.** The tool recommends and never executes.
2. **Untrusted input.** Everything from monitoring data is treated as data, never instructions.
3. **Provider neutral.** Model choice is configuration, not architecture.
4. **Measured quality.** No model or prompt change ships without the evaluation set.
5. **Least data.** Send only what the model needs.

## Open risks

| Risk | Mitigation |
|---|---|
| Prompt injection via incident fields | Tagged and sanitised context, system prompt, script deny-list, human review |
| Harmful or wrong generated scripts | Risk labels, auto-flagging, rollback scripts, "review before running" warnings |
| Sensitive data sent to a model | Approved providers only; Ollama for local-only use; field minimisation |
| Cost growth | Cache with TTL, dedupe, rate limits, Sonnet by default |
| Model drift or regression | Evaluation harness in CI |
| Recovery validation is a model judgement, not a metric check | Customers may over-trust "recovered"; show remaining checks; metric-based validation through DQL (3A) |
| No login and no user recorded in history | Keep the loopback bind or an authenticating proxy; SSO and per-user identity in Phase 2 |
| Model access uses a personal API key | Dynatrace-approved access (Phase 2); use only approved providers with real incident data |
| Ownership and licence of the code are not yet confirmed for a Dynatrace customer product | Confirm the IP position with management and legal before pilot or rollout; the current `LICENSE` names an individual copyright holder |
