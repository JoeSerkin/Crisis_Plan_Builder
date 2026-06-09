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
3. **Modular agents** — Specialized agents with typed JSON outputs

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

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

## Knowledge base

- **~105 requirements** in `knowledge/crisis_management/requirements_catalog.yaml` (universal + industry-scoped)
- **Industry modifiers:** manufacturing, energy, pharma, NGO (`knowledge/risk_assessment/industry_modifiers/`)
- Industry-specific requirements activate only when the intake industry matches a modifier

## Demo: sparse → enriched → full plan

Requires `pip install -e ".[dev,workflow]"`.

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

## Full workflow (optional)

Requires readiness score ≥ 60 and `workflow` extra:

```bash
pip install -e ".[dev,workflow]"
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

## License

Private / consultant use. Deliverables are drafts for professional review.
