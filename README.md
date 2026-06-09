# Crisis Management Planner

AI-powered agent system that assists consultants in creating professional crisis management plans. This is an **agentic workflow** that produces consulting-grade deliverables — not a chatbot.

## Primary users

- Crisis management consultants
- Security consultants
- Business continuity professionals
- Travel risk management providers
- Corporate security teams

## Design principles

1. **Structured methodology** — Assess → Gaps → Risk → Governance → Procedures → Review → Deliverables
2. **Human-in-the-loop** — Consultant remains decision-maker; agents identify gaps and recommend options
3. **Organizational flexibility** — Size, maturity, staffing, and jurisdiction calibrate gap priorities and CMT design
4. **Modular agents** — Specialized agents with typed JSON outputs

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[test]"

# Run Milestone 1 — Client Discovery
python -m cmp.workflows.discovery_cli ^
  --engagement example-mfg ^
  --input tests/fixtures/example_manufacturing_intake.json ^
  --no-llm
```

## Agents

| Agent | Module | Output |
|-------|--------|--------|
| Client Discovery | `cmp.agents.discovery` | Gap analysis + readiness score |
| Risk Profiling | `cmp.agents.risk_profile` | Tier 1/2/3 risks |
| Governance Design | `cmp.agents.governance` | CMT, escalation, authorities |
| Procedure Builder | `cmp.agents.procedures` | Per-risk procedures |
| Standards Review | `cmp.agents.reviewer` | Framework coverage assessment |
| Tabletop Exercise | `cmp.agents.tabletop` | Scenario + injects |

## Deliverables

Full planner runs write Markdown files to `output/{engagement_id}/`:

| File | Content |
|------|---------|
| `crisis_management_plan.md` | Integrated plan |
| `gap_analysis_report.md` | Discovery gaps and readiness |
| `risk_register.md` | Tier 1/2/3 risk register |
| `escalation_matrix.md` | Severity levels, notification matrix, authorities |
| `incident_procedures.md` | Combined procedure pack |
| `procedures/{risk_id}.md` | Individual procedure per risk |
| `tabletop_exercise.md` | Exercise scenario and injects |

## Knowledge base

- **~120 requirements** in `knowledge/crisis_management/requirements_catalog.yaml` (universal + industry-scoped)
- **Industry modifiers:** manufacturing, energy, pharma, NGO (`knowledge/risk_assessment/industry_modifiers/`)
- **Demo engagements:** `example-mfg` (medium manufacturing), `example-ngo` (small humanitarian)
- Industry-specific requirements activate only when the intake industry matches a modifier

## Demo: sparse → enriched → full plan

Requires `pip install -e ".[test,v2]"`.

```bash
# 1. Sparse discovery (score ~5, blocked at readiness gate)
python -m cmp.workflows.discovery_cli ^
  --engagement example-mfg ^
  --input tests/fixtures/example_manufacturing_intake.json ^
  --no-llm

# 2. Merge enriched consultant answers and re-run discovery (score ≥ 60)
python -m cmp.workflows.merge_intake_cli ^
  --engagement example-mfg ^
  --updates tests/fixtures/example_mfg_merge_updates.json
python -m cmp.workflows.discovery_cli ^
  --engagement example-mfg ^
  --input storage/engagements/example-mfg/intake.json ^
  --no-llm

# 3. Full planner workflow (produces deliverables under output/example-mfg/)
python -m cmp.workflows.planner_cli ^
  --engagement example-mfg ^
  --input storage/engagements/example-mfg/intake.json
```

Enriched intake fixture: `tests/fixtures/example_manufacturing_intake_enriched.json`

## Demo: NGO (small humanitarian)

Shows **lean CMT**, **field security gaps**, and **UK HQ jurisdiction** notes for a 45-person iNGO operating in Kenya and South Sudan.

```bash
# 1. Sparse discovery (score ~4, 16 critical gaps including field security)
python -m cmp.workflows.discovery_cli ^
  --engagement example-ngo ^
  --input tests/fixtures/example_ngo_intake.json ^
  --no-llm

# 2. Merge enriched answers + re-run discovery (score ≥ 60, lean CMT)
python -m cmp.workflows.merge_intake_cli ^
  --engagement example-ngo ^
  --updates tests/fixtures/example_ngo_merge_updates.json
python -m cmp.workflows.discovery_cli ^
  --engagement example-ngo ^
  --input storage/engagements/example-ngo/intake.json ^
  --no-llm

# 3. Full planner workflow
python -m cmp.workflows.planner_cli ^
  --engagement example-ngo ^
  --input storage/engagements/example-ngo/intake.json
```

Fixtures: `tests/fixtures/example_ngo_intake.json`, `example_ngo_intake_enriched.json`

## Consultant playbook (merge vs resolve)

| Situation | Action |
|-----------|--------|
| Client provided new facts (contacts, policies, sites) | `merge_intake_cli --updates answers.json` then re-run discovery |
| Gap is intentionally N/A for this client (e.g. no OT/ICS) | `merge_intake_cli --resolve REQ-ID` — consultant override, not client data |
| Industry/size context changes expectations | Set `organization_size`, `staffing_model`, `headquarters_country` in intake — discovery adapts automatically |
| Readiness still below 60 | Fill **critical** gaps first (score capped at 40 until cleared), then high-priority fields |

Never use `--resolve` to skip gaps without consultant sign-off. Resolved IDs are stored on the engagement record and excluded from future gap detection.

## Full workflow (optional)

Requires readiness score ≥ 60 and `workflow` extra:

```bash
pip install -e ".[test,v2]"
python -m cmp.workflows.planner_cli --engagement example-mfg --input path/to/intake.json
```

## Project structure

```
src/cmp/           Python package
knowledge/         Requirements catalog and reference content (RAG-ready)
storage/           Engagement artifacts (gitignored)
output/            Generated deliverables (gitignored)
tests/             Pytest suite
.cursor/           Cursor skill and rules
```

## Tests

```bash
pytest
```

## V2 API and web UI (Build 5)

Install the V2 stack:

```bash
python -m pip install --upgrade pip   # required on Python 3.14 with pip < 26
pip install -e .
pip install -r requirements-v2.txt
python -m cmp.api.server --host 127.0.0.1 --port 8000
```

Or, after upgrading pip:

```bash
pip install -e ".[v2]"
python -m cmp.api.server --host 127.0.0.1 --port 8000
```

> **Python 3.14:** pip 25.x fails on optional extras with `Invalid version: 'docx'` (or similar). Upgrade pip first, or use the two-step install above.

> **Windows PATH:** If `cmp-api` is not recognized, use `python -m cmp.api.server` (same command). Pip may install console scripts to `%APPDATA%\Python\Python314\Scripts` — add that folder to PATH if you prefer the `cmp-api` shortcut.

Open http://127.0.0.1:8000 for the consultant UI, or call the REST API directly:

### Client intake questionnaire

Send clients to **http://127.0.0.1:8000/intake** (optionally `?industry=Manufacturing&engagement=client-id`).

The form is generated from the requirements catalog (~90+ questions, filtered by industry) with dropdowns and multi-select where relevant. Clients can **download JSON** or **save directly to an engagement** for discovery.

The consultant console (`/`) now supports the full workflow in browser tabs:

| Tab | Capabilities |
|-----|----------------|
| **Workflow** | Stepper, readiness score, guided **Continue** action |
| **Gaps & merge** | Review open gaps, apply values, mark N/A (resolve), paste JSON merge |
| **Documents** | Upload PDF/DOCX/TXT/JSON, extract proposed intake answers, apply with re-discovery |
| **Deliverables** | View markdown, download markdown/DOCX |

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check |
| POST | `/api/v1/engagements` | Create engagement + intake |
| GET | `/api/v1/engagements/{id}/workflow` | Workflow status, steps, and next action |
| GET | `/api/v1/engagements/{id}/gaps` | Gap list with resolve status and questions |
| POST | `/api/v1/engagements/{id}/discovery` | Run discovery |
| POST | `/api/v1/engagements/{id}/merge` | Merge updates / resolve gaps (re-runs discovery) |
| POST | `/api/v1/engagements/{id}/documents/upload` | Upload PDF, DOCX, TXT, MD, JSON |
| POST | `/api/v1/engagements/{id}/documents/{doc}/extract` | Propose intake updates from document |
| POST | `/api/v1/engagements/{id}/documents/apply` | Apply selected proposals + re-run discovery |
| GET | `/api/v1/engagements/{id}/download/markdown/{path}` | Download markdown deliverable |
| GET | `/api/v1/engagements/{id}/download/docx/{path}` | Download DOCX deliverable |
| POST | `/api/v1/engagements/{id}/plan` | Full planner workflow |
| GET | `/api/v1/engagements/{id}/deliverables` | List markdown deliverables |
| POST | `/api/v1/engagements/{id}/export/docx` | Export deliverables to DOCX |
| GET | `/api/v1/knowledge/search?q=…` | Search knowledge base |
| GET | `/api/v1/intake-form/schema?industry=…` | Client form schema |
| POST | `/api/v1/intake-form/submit` | Convert form answers → intake JSON |
| POST | `/api/v1/intake-form/submit/{id}` | Save client form to engagement |

DOCX files are written to `output/{engagement_id}/docx/`.

### Install Cursor skill globally

Copy or symlink this repo's skill into your user skills folder so other projects can invoke it:

```powershell
# Windows — junction (no admin required)
New-Item -ItemType Junction -Path "$env:USERPROFILE\.cursor\skills\crisis-management-planner" `
  -Target "$PWD\.cursor\skills\crisis-management-planner"
```

### V2 roadmap (remaining)

- PDF export
- Vector embeddings RAG (current search is keyword-based)
- travel-risk-map overlay integration (`knowledge/risk_assessment/travel_overlay.yaml` stub in place)

## License

Private / consultant use. Deliverables are drafts for professional review.
