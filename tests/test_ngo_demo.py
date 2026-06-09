"""NGO industry demo — sparse intake, enriched gate, lean CMT, full workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cmp.agents.discovery import run_discovery
from cmp.agents.governance import run_governance
from cmp.agents.procedures import run_procedures
from cmp.agents.reviewer import run_standards_review
from cmp.agents.risk_profile import run_risk_profile
from cmp.models.schemas import ClientIntake

FIXTURES = Path(__file__).parent / "fixtures"

pytest.importorskip("langgraph")


@pytest.fixture
def sparse_ngo_intake() -> ClientIntake:
    data = json.loads((FIXTURES / "example_ngo_intake.json").read_text(encoding="utf-8"))
    return ClientIntake.model_validate(data)


@pytest.fixture
def enriched_ngo_intake() -> ClientIntake:
    data = json.loads((FIXTURES / "example_ngo_intake_enriched.json").read_text(encoding="utf-8"))
    return ClientIntake.model_validate(data)


def test_humanitarian_ngo_industry_modifier_matches(sparse_ngo_intake: ClientIntake) -> None:
    output = run_discovery(sparse_ngo_intake, use_llm_questions=False)
    assert any("[industry_context]" in note for note in output.assumptions)
    gap_ids = {g.requirement_id for g in output.missing_information}
    assert "RISK-023" in gap_ids
    assert "GOV-020" in gap_ids
    assert "OPS-010" not in gap_ids


def test_sparse_ngo_small_org_context(sparse_ngo_intake: ClientIntake) -> None:
    output = run_discovery(sparse_ngo_intake, use_llm_questions=False)
    assert output.organization_context is not None
    assert output.organization_context.size_tier == "small"
    assert output.planning_readiness_score < 60
    assert len(output.critical_gaps) >= 10


def test_sparse_ngo_lean_governance(sparse_ngo_intake: ClientIntake) -> None:
    discovery = run_discovery(sparse_ngo_intake, use_llm_questions=False)
    gov = run_governance(discovery)
    assert len(gov.crisis_team_roles) == 4
    assert gov.crisis_team_roles[0].role == "Crisis Lead"


def test_enriched_ngo_passes_readiness_gate(enriched_ngo_intake: ClientIntake) -> None:
    output = run_discovery(enriched_ngo_intake, use_llm_questions=False)
    assert output.critical_gaps == []
    assert output.planning_readiness_score >= 60
    assert output.organization_context is not None
    assert output.organization_context.size_tier == "small"


def test_enriched_ngo_risk_profile_and_review(enriched_ngo_intake: ClientIntake) -> None:
    discovery = run_discovery(enriched_ngo_intake, use_llm_questions=False)
    profile = run_risk_profile(enriched_ngo_intake, discovery)
    gov = run_governance(discovery)
    procs = run_procedures(profile)
    review = run_standards_review(discovery, gov, procs)

    assert any("field" in risk.title.lower() or "duty" in risk.title.lower() for risk in profile.tier_1_risks)
    assert review.framework_coverage_score == 100
    assert review.gaps == []


def test_ngo_planner_completes(enriched_ngo_intake: ClientIntake) -> None:
    from cmp.workflows.planner_graph import run_planner

    result = run_planner("pytest-enriched-ngo", enriched_ngo_intake)
    assert result["status"] == "complete"
    assert result["discovery"]["planning_readiness_score"] >= 60
