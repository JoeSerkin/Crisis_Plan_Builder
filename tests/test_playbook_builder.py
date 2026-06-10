"""Tests for role-based playbook generation."""

from __future__ import annotations

import json
from pathlib import Path

from cmp.agents.governance import run_governance
from cmp.agents.risk_profile import run_risk_profile
from cmp.agents.discovery import run_discovery
from cmp.models.schemas import ClientIntake
from cmp.render.playbook_builder import build_role_playbook, build_scenario_procedure, roster_from_governance

FIXTURES = Path(__file__).parent / "fixtures"


def test_playbook_roles_have_prose_sections() -> None:
    data = json.loads((FIXTURES / "example_manufacturing_intake_enriched.json").read_text(encoding="utf-8"))
    intake = ClientIntake.model_validate(data)
    discovery = run_discovery(intake, use_llm_questions=False)
    gov = run_governance(discovery)
    playbook = build_role_playbook(gov)

    assert len(playbook.roles) >= 4
    role = playbook.roles[0]
    assert role.first_15_minutes
    assert role.during_response
    assert len(role.decisions) >= 1


def test_scenario_card_activates_roles_not_generic_bullets() -> None:
    data = json.loads((FIXTURES / "example_manufacturing_intake_enriched.json").read_text(encoding="utf-8"))
    intake = ClientIntake.model_validate(data)
    discovery = run_discovery(intake, use_llm_questions=False)
    gov = run_governance(discovery)
    profile = run_risk_profile(intake, discovery)
    risk = profile.tier_1_risks[0]
    roster = roster_from_governance(gov)

    card = build_scenario_procedure(risk, gov, roster)
    assert card.procedure.crisis_level == 3
    assert len(card.procedure.role_actions) >= 2
    assert all(action.summary for action in card.procedure.role_actions)
    assert "Ensure personnel safety" not in card.procedure.opening_steps or "life safety" in card.procedure.opening_steps
