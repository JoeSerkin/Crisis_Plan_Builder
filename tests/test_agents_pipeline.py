"""Integration tests for downstream agents and deliverable rendering."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cmp.agents.discovery import run_discovery
from cmp.agents.governance import run_governance
from cmp.agents.procedures import run_procedures
from cmp.agents.reviewer import run_standards_review
from cmp.agents.risk_profile import run_risk_profile
from cmp.agents.tabletop import run_tabletop
from cmp.models.schemas import ClientIntake
from cmp.render.deliverables import render_crisis_management_plan, render_gap_analysis

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def manufacturing_intake() -> ClientIntake:
    data = json.loads((FIXTURES / "example_manufacturing_intake.json").read_text(encoding="utf-8"))
    return ClientIntake.model_validate(data)


def test_risk_profile_manufacturing(manufacturing_intake: ClientIntake) -> None:
    discovery = run_discovery(manufacturing_intake, use_llm_questions=False)
    profile = run_risk_profile(manufacturing_intake, discovery)
    assert len(profile.tier_1_risks) >= 3
    assert any("industrial" in r.title.lower() or "supply" in r.title.lower() for r in profile.tier_1_risks)


def test_governance_structure(manufacturing_intake: ClientIntake) -> None:
    discovery = run_discovery(manufacturing_intake, use_llm_questions=False)
    gov = run_governance(discovery)
    assert len(gov.crisis_levels) == 4
    assert len(gov.crisis_team_roles) >= 5
    assert len(gov.escalation_matrix) >= 4


def test_procedures_from_risks(manufacturing_intake: ClientIntake) -> None:
    discovery = run_discovery(manufacturing_intake, use_llm_questions=False)
    profile = run_risk_profile(manufacturing_intake, discovery)
    procs = run_procedures(profile)
    assert len(procs.procedures) >= 3
    for proc in procs.procedures:
        assert proc.procedure.immediate_actions
        assert proc.procedure.escalation_triggers


def test_standards_review(manufacturing_intake: ClientIntake) -> None:
    discovery = run_discovery(manufacturing_intake, use_llm_questions=False)
    gov = run_governance(discovery)
    profile = run_risk_profile(manufacturing_intake, discovery)
    procs = run_procedures(profile)
    review = run_standards_review(discovery, gov, procs)
    assert 0 <= review.framework_coverage_score <= 100
    assert review.recommendations


def test_tabletop_from_risks(manufacturing_intake: ClientIntake) -> None:
    profile = run_risk_profile(manufacturing_intake)
    tabletop = run_tabletop(profile)
    assert tabletop.scenario
    assert len(tabletop.injects) >= 3
    assert tabletop.learning_objectives


def test_render_deliverables(manufacturing_intake: ClientIntake) -> None:
    discovery = run_discovery(manufacturing_intake, use_llm_questions=False)
    gov = run_governance(discovery)
    profile = run_risk_profile(manufacturing_intake, discovery)
    procs = run_procedures(profile)
    review = run_standards_review(discovery, gov, procs)
    plan = render_crisis_management_plan(
        manufacturing_intake.company_name, discovery, gov, procs, review
    )
    gap = render_gap_analysis(discovery, manufacturing_intake.company_name)
    assert "Example Manufacturing" in plan
    assert "DRAFT" in plan
    assert "Planning readiness score" in gap
