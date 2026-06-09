"""Tests for client intake form schema."""

from __future__ import annotations

from cmp.intake.form_schema import answers_to_intake, build_client_form_schema, validate_intake_payload


def test_universal_form_has_core_fields() -> None:
    schema = build_client_form_schema()
    paths = {
        field["field_path"]
        for section in schema["sections"]
        for field in section["fields"]
    }
    assert "company_name" in paths
    assert "countries" in paths
    assert "crisis_team_structure" in paths
    assert schema["field_count"] >= 90


def test_manufacturing_form_includes_industry_fields() -> None:
    schema = build_client_form_schema("Manufacturing")
    paths = {
        field["field_path"]
        for section in schema["sections"]
        for field in section["fields"]
    }
    assert "production_continuity" in paths
    assert "pipeline_infrastructure" not in paths


def test_answers_to_intake_splits_top_level_and_context() -> None:
    payload = answers_to_intake(
        {
            "company_name": "Acme Corp",
            "industry": "Manufacturing",
            "countries": ["Germany", "Mexico"],
            "employees": "500",
            "crisis_team_structure": "Crisis Director: COO",
        },
        industry="Manufacturing",
    )
    intake = validate_intake_payload(payload)
    assert intake.company_name == "Acme Corp"
    assert intake.employees == 500
    assert intake.additional_context["crisis_team_structure"] == "Crisis Director: COO"


def test_select_fields_use_widget_overrides() -> None:
    schema = build_client_form_schema()
    fields = {f["field_path"]: f for section in schema["sections"] for f in section["fields"]}
    assert fields["organization_size"]["type"] == "select"
    assert fields["countries"]["type"] == "multiselect"
    assert fields["existing_crisis_plan"]["type"] == "select"
