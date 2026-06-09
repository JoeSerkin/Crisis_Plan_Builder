"""Golden-file tests for Client Discovery Agent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cmp.agents.discovery import map_known_information, run_discovery
from cmp.models.schemas import ClientIntake

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def manufacturing_intake() -> ClientIntake:
    data = json.loads((FIXTURES / "example_manufacturing_intake.json").read_text(encoding="utf-8"))
    return ClientIntake.model_validate(data)


def test_known_information_no_fabrication(manufacturing_intake: ClientIntake) -> None:
    known = map_known_information(manufacturing_intake)
    assert set(known.keys()) == {"company_name", "industry", "employees", "countries"}
    assert known["company_name"].value == "Example Manufacturing"
    assert known["industry"].value == "Manufacturing"
    assert known["employees"].value == 500
    assert known["countries"].value == ["Germany", "Mexico", "Thailand"]
    for field in known.values():
        assert field.source == "intake"
        assert field.confidence.value == "stated_by_client"


def test_sparse_intake_critical_gaps(manufacturing_intake: ClientIntake) -> None:
    output = run_discovery(manufacturing_intake, use_llm_questions=False)
    assert len(output.critical_gaps) >= 5
    expected_subset = {
        "GOV-003",  # CMT structure
        "GOV-004",  # activation criteria
        "GOV-008",  # 24/7 escalation
        "COM-002",  # spokesperson
        "OPS-001",  # site registry
    }
    assert expected_subset.issubset(set(output.critical_gaps))


def test_planning_readiness_score_below_threshold(manufacturing_intake: ClientIntake) -> None:
    output = run_discovery(manufacturing_intake, use_llm_questions=False)
    assert output.planning_readiness_score < 50


def test_enriched_intake_increases_score(manufacturing_intake: ClientIntake) -> None:
    sparse = run_discovery(manufacturing_intake, use_llm_questions=False)
    enriched = ClientIntake.model_validate(
        {
            **manufacturing_intake.model_dump(),
            "legal_entities": [{"name": "Example Manufacturing GmbH", "country": "Germany"}],
            "sites": [{"name": "Plant A", "country": "Germany"}],
            "additional_context": {
                "crisis_team_structure": {"crisis_director": "Jane Doe"},
                "crisis_activation_criteria": ["Fatalities", "Regulatory notification"],
                "after_hours_escalation": [{"name": "On-call Manager", "phone": "+1-555-0100"}],
                "spokesperson_policy": {"primary": "Communications Director"},
                "existing_crisis_plan": "2019 plan, not updated",
                "critical_functions": ["Production"],
                "site_activation_contacts": [{"site": "Plant A", "primary": "Site Manager"}],
                "decision_authorities": {"shutdown": "Plant Director"},
                "escalation_matrix": [{"level": 1, "notify": "Site Manager"}],
                "internal_comms_channels": ["Teams bridge"],
                "existing_bcp": "Site BCP exists",
                "cyber_incident_playbook": "IT IR playbook v1",
                "supply_chain_critical_suppliers": [{"name": "Supplier X"}],
                "industrial_accident_scenarios": ["Fire", "Chemical release"],
                "site_crisis_leads": [{"country": "Germany", "lead": "Country GM"}],
            },
        }
    )
    rich = run_discovery(enriched, use_llm_questions=False)
    assert rich.planning_readiness_score > sparse.planning_readiness_score
    assert len(rich.critical_gaps) < len(sparse.critical_gaps)


def test_recommended_questions_match_gaps(manufacturing_intake: ClientIntake) -> None:
    output = run_discovery(manufacturing_intake, use_llm_questions=False)
    gap_ids = {g.requirement_id for g in output.missing_information}
    question_targets = {q.targets_gap for q in output.recommended_questions}
    assert question_targets == gap_ids


def test_readiness_breakdown_has_all_domains(manufacturing_intake: ClientIntake) -> None:
    output = run_discovery(manufacturing_intake, use_llm_questions=False)
    for domain in ("org_profile", "operations_sites", "governance", "communications", "risk_bcp"):
        assert domain in output.readiness_breakdown


def test_enriched_intake_passes_readiness_gate() -> None:
    data = json.loads(
        (FIXTURES / "example_manufacturing_intake_enriched.json").read_text(encoding="utf-8")
    )
    intake = ClientIntake.model_validate(data)
    output = run_discovery(intake, use_llm_questions=False)
    assert output.critical_gaps == []
    assert output.planning_readiness_score >= 60
    high_gaps = [g for g in output.missing_information if g.priority.value == "high"]
    assert high_gaps == []
