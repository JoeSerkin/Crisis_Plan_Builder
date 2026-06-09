"""Tests for document extraction heuristics."""

from __future__ import annotations

import json
from pathlib import Path

from cmp.intake.document_extract import (
    propose_updates_from_document,
    propose_updates_from_text,
)
from cmp.models.schemas import ClientIntake, RequirementGap


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
