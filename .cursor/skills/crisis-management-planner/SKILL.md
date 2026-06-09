---
name: crisis-management-planner
description: >-
  Cursor-operated crisis management planning agent system for consultants.
  Produces structured gap analysis, risk profiles, governance designs, procedures,
  standards review, and deliverables. Triggers on crisis management plan, CMT design,
  crisis discovery, gap analysis, tabletop exercise, or ISO 22361 planning requests.
---

# Crisis Management Planner

Consultant-grade **agentic workflow** — not a chatbot. Follow the phased methodology; never jump from a company description to a completed crisis plan.

## Methodology (mandatory sequence)

1. **Assess** — Client Discovery Agent
2. **Identify Gaps** — Consultant reviews questions; merge answers into intake
3. **Analyze Risks** — Risk Profiling Agent (gate: readiness ≥ 60)
4. **Design Framework** — Governance Design Agent
5. **Generate Procedures** — Procedure Builder Agent
6. **Review** — Standards Review Agent
7. **Produce Deliverables** — Jinja2 templates → `output/{engagement_id}/`

## Phase gates

| Phase | Gate |
|-------|------|
| Discovery → Risk Profiling | `planning_readiness_score >= 60` |
| Any deliverable | Consultant review required; label as DRAFT |
| Standards review | `framework_coverage_score` is coverage, not certification |

## Human-in-the-loop

- Ask clarifying questions from `recommended_questions`; do not invent org details
- Highlight assumptions in `assumptions[]`
- After client answers, merge into intake and re-run discovery
- Consultant is the decision-maker on all recommendations

## Organizational flexibility

The process adapts to client context — it is not a one-size-fits-all checklist:

- **Size tier** (small / medium / large / enterprise) — inferred from `employees` or set via `organization_size`
- **Maturity** (`crisis_program_maturity`: nascent / developing / established) — calibrates phased expectations
- **Staffing model** (`staffing_model`: lean / centralized / distributed) — affects CMT design and alternates
- **Jurisdiction** — `headquarters_country` and `countries[]` drive legal, insurance, and cultural assumptions

Discovery emits `organization_context` plus tagged assumptions:

- `[org_flexibility]` — size/maturity/staffing guidance
- `[jurisdiction]` — country-specific legal and insurance notes

Small organizations may use a **lean CMT** (combined roles with named alternates). Multi-country clients retain stricter site-level and regulatory requirements. Consultants may still `--resolve` requirement IDs when a gap is intentionally out of scope.

## Repository layout

- Package: `src/cmp/`
- Knowledge: `knowledge/crisis_management/requirements_catalog.yaml`
- Client data: `storage/engagements/{engagement_id}/` (gitignored)
- Deliverables: `output/{engagement_id}/`

Full planner output (v1.4+):

| File | Purpose |
|------|---------|
| `crisis_management_plan.md` | Integrated plan |
| `gap_analysis_report.md` | Gaps and readiness score |
| `risk_register.md` | Tier 1/2/3 risks |
| `escalation_matrix.md` | Severity levels, notification matrix, authorities |
| `incident_procedures.md` | Combined procedure pack |
| `procedures/{risk_id}.md` | One procedure per risk |
| `tabletop_exercise.md` | Exercise scenario |

## Commands

### Setup

```bash
cd crisis-management-planner
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
```

Optional workflow (full planner):

```bash
pip install -e ".[dev,workflow]"
```

Optional LLM question phrasing:

```bash
pip install -e ".[dev,llm]"
set GEMINI_API_KEY=...
```

### Milestone 1 — Discovery only

```bash
python -m cmp.workflows.discovery_cli ^
  --engagement example-mfg ^
  --input tests/fixtures/example_manufacturing_intake.json ^
  --no-llm
```

### Merge consultant answers

```bash
python -m cmp.workflows.merge_intake_cli ^
  --engagement example-mfg ^
  --updates path/to/updates.json ^
  --resolve GOV-003 GOV-004
```

Then re-run discovery.

### Full workflow (after readiness gate passes)

```bash
python -m cmp.workflows.planner_cli ^
  --engagement example-mfg ^
  --input storage/engagements/example-mfg/intake.json
```

### NGO demo (small humanitarian)

```bash
python -m cmp.workflows.discovery_cli ^
  --engagement example-ngo ^
  --input tests/fixtures/example_ngo_intake.json ^
  --no-llm
```

Fixtures: `tests/fixtures/example_ngo_intake.json`, `example_ngo_intake_enriched.json`

## Output contracts

### Discovery

```json
{
  "known_information": {},
  "missing_information": [],
  "critical_gaps": [],
  "recommended_questions": [],
  "assumptions": [],
  "organization_context": {},
  "planning_readiness_score": 0,
  "readiness_breakdown": {}
}
```

`known_information` must contain **only** intake-mapped fields — never fabricated contacts or authorities.

## Quality bar

- Every gap traces to a `requirement_id` in the catalog
- Critical gaps weighted in readiness score (cap at 40 while unresolved)
- Deliverables include "DRAFT — For consultant review. Not ISO certification."
- Separate fact from inference in all client-facing text

## Out of scope (V1)

- FastAPI / web UI
- Live OSINT on clients
- ISO certification claims
- Automatic client data upload to cloud
