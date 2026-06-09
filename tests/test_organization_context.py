"""Tests for organization size, maturity, and jurisdiction context."""

from __future__ import annotations

import json
from pathlib import Path

from cmp.agents.discovery import run_discovery
from cmp.agents.governance import run_governance
from cmp.models.organization_context import resolve_organization_context
from cmp.models.schemas import ClientIntake

FIXTURES = Path(__file__).parent / "fixtures"


def test_small_organization_inferred_from_headcount() -> None:
    intake = ClientIntake(
        company_name="Small Co",
        industry="Professional Services",
        employees=25,
        countries=["Ireland"],
    )
    context = resolve_organization_context(intake)
    assert context.size_tier == "small"
    assert context.min_cmt_roles == 3


def test_jurisdiction_notes_for_eu_footprint() -> None:
    intake = ClientIntake(
        company_name="EU Co",
        industry="Manufacturing",
        employees=120,
        countries=["Germany"],
        headquarters_country="Germany",
    )
    output = run_discovery(intake, use_llm_questions=False)
    assert output.organization_context is not None
    assert any("[jurisdiction]" in note for note in output.assumptions)
    assert any("GDPR" in note for note in output.organization_context.jurisdiction_notes)


def test_small_org_uses_lean_governance_team() -> None:
    intake = ClientIntake(
        company_name="Small Co",
        industry="NGO",
        employees=20,
        countries=["Kenya"],
        organization_size="small",
        staffing_model="lean",
    )
    discovery = run_discovery(intake, use_llm_questions=False)
    gov = run_governance(discovery)
    assert len(gov.crisis_team_roles) == 4
    assert gov.crisis_team_roles[0].role == "Crisis Lead"


def test_multi_country_manufacturing_keeps_site_crisis_leads_critical() -> None:
    data = json.loads((FIXTURES / "example_manufacturing_intake.json").read_text(encoding="utf-8"))
    intake = ClientIntake.model_validate(data)
    output = run_discovery(intake, use_llm_questions=False)
    assert "GOV-012" in output.critical_gaps
