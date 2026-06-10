"""Tests for document extraction heuristics."""

from __future__ import annotations

import json
from pathlib import Path

from cmp.intake.document_extract import (
    propose_updates_from_document,
    propose_updates_from_text,
)
from cmp.models.requirements import (
    filter_requirements_for_industry,
    load_industry_modifier,
    load_requirements_catalog,
)
from cmp.models.schemas import ClientIntake, RequirementGap

FIXTURES = Path(__file__).parent / "fixtures"


def _gap(requirement_id: str, field_path: str, label: str) -> RequirementGap:
    return RequirementGap(
        requirement_id=requirement_id,
        domain="governance",
        label=label,
        priority="high",
        why_it_matters="Needed for planning.",
        field_path=field_path,
    )


def test_propose_updates_from_label_value_lines() -> None:
    text = """
Crisis Management Team Leader: Jane Doe
Emergency hotline: +49 30 1234567
Total employees: 500 employees globally
"""
    gaps = [
        _gap("GOV-001", "cmt_leader_name", "Crisis management team leader"),
        _gap("COM-001", "emergency_hotline", "Emergency hotline number"),
        _gap("ORG-003", "employees", "Total employee count"),
    ]
    proposals = propose_updates_from_text(text, gaps)
    by_field = {item.field_path: item.proposed_value for item in proposals}
    assert by_field["cmt_leader_name"] == "Jane Doe"
    assert "1234567" in str(by_field["emergency_hotline"])
    assert by_field["employees"] == 500


def test_propose_updates_from_json_upload(tmp_path: Path) -> None:
    payload = {"headquarters_country": "Germany", "additional_context": {"cmt_leader_name": "Alex Smith"}}
    path = tmp_path / "updates.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    gaps = [
        _gap("ORG-008", "headquarters_country", "Headquarters country"),
        _gap("GOV-001", "cmt_leader_name", "Crisis management team leader"),
    ]
    _, proposals = propose_updates_from_document(path, gaps)
    by_field = {item.field_path: item.proposed_value for item in proposals}
    assert by_field["headquarters_country"] == "Germany"
    assert by_field["cmt_leader_name"] == "Alex Smith"


def test_propose_updates_skips_present_intake_fields() -> None:
    intake = ClientIntake.model_validate(
        {
            "company_name": "Example Co",
            "industry": "Manufacturing",
            "countries": ["Germany"],
            "employees": 500,
        }
    )
    gaps = [_gap("ORG-003", "employees", "Total employee count")]
    proposals = propose_updates_from_text("Employees: 750", gaps, intake=intake)
    assert proposals == []


def _ngo_catalog_gaps() -> list[RequirementGap]:
    catalog = load_requirements_catalog()
    modifier = load_industry_modifier("Humanitarian NGO")
    requirements = filter_requirements_for_industry(catalog, modifier)
    return [
        RequirementGap(
            requirement_id=req.id,
            domain=req.domain,
            label=req.label,
            priority=req.priority,
            why_it_matters=req.why_it_matters,
            unlocks_agents=req.unlocks_agents,
            field_path=req.field_path,
        )
        for req in requirements
    ]


def test_israaid_dominica_emergency_plan_extraction() -> None:
    text = (FIXTURES / "israaid_dominica_emergency_plan.txt").read_text(encoding="utf-8")
    gaps = _ngo_catalog_gaps()
    proposals = propose_updates_from_text(text, gaps)
    by_field = {item.field_path: item for item in proposals}

    assert by_field["existing_crisis_plan"].proposed_value == "yes"
    assert by_field["company_name"].proposed_value == "IsraAID"
    assert "Dominica" in by_field["countries"].proposed_value
    assert by_field["headquarters_country"].proposed_value == "Dominica"

    team = by_field["crisis_team_structure"].proposed_value
    assert isinstance(team, list)
    team_text = json.dumps(team)
    assert "Paul Norris" in team_text
    assert "Hannah Gaventa" in team_text
    assert "Air Mattress" not in team_text

    levels = by_field["crisis_levels"].proposed_value
    assert "Level 1" in levels
    assert "Level 3" in levels

    hazards = by_field["risk_register"].proposed_value
    assert "Hurricanes" in hazards
    assert "Earthquakes" in hazards

    sites = by_field["sites"].proposed_value
    site_names = {site["name"] for site in sites}
    assert "Portsmouth" in site_names
    assert "Roseau office" in site_names

    assert "whatsapp" in by_field["internal_comms_channels"].proposed_value.lower()
    assert len(proposals) >= 12
