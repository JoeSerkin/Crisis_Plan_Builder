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


def test_client_form_uses_plain_language_sections() -> None:
    schema = build_client_form_schema()
    labels = [section["label"] for section in schema["sections"]]
    assert "About your organization" in labels
    assert "Organization Profile" not in labels


def test_client_form_avoids_consultant_jargon_in_questions() -> None:
    schema = build_client_form_schema("Manufacturing")
    questions = [
        field["question"]
        for section in schema["sections"]
        for field in section["fields"]
    ]
    joined = " ".join(questions).lower()
    assert "ot/ics" not in joined
    assert "tabletop" not in joined
    assert "rpo/rto" not in joined
    fields = {f["field_path"]: f for section in schema["sections"] for f in section["fields"]}
    assert fields["crisis_team_structure"]["label"] == "Emergency leadership team"
    assert fields["escalation_matrix"]["label"] == "Who to notify and when"


def test_select_fields_use_widget_overrides() -> None:
    schema = build_client_form_schema()
    fields = {f["field_path"]: f for section in schema["sections"] for f in section["fields"]}
    assert fields["organization_size"]["type"] == "select"
    assert fields["countries"]["type"] == "country_multiselect"
    assert fields["existing_crisis_plan"]["type"] == "select"
    assert fields["sites"]["type"] == "site_list"


def test_ngo_form_excludes_commercial_fields() -> None:
    schema = build_client_form_schema("Humanitarian NGO")
    paths = {
        field["field_path"]
        for section in schema["sections"]
        for field in section["fields"]
    }
    assert "business_model" not in paths
    assert "key_customers" not in paths
    assert "ot_ics_security" not in paths
    assert "local_partner_vetting" in paths


def test_manufacturing_includes_ot_security() -> None:
    schema = build_client_form_schema("Manufacturing")
    fields = {f["field_path"]: f for section in schema["sections"] for f in section["fields"]}
    assert fields["ot_ics_security"]["type"] == "compound"
    assert fields["travel_exposure"]["type"] == "compound"


def test_compound_answers_merge_into_structured_context() -> None:
    payload = answers_to_intake(
        {
            "company_name": "Acme",
            "travel_international_trips": "30",
            "travel_high_risk_trips": "5",
            "travel_high_risk_destinations": ["Mexico", "Kenya"],
            "travel_destinations_notes": "Nairobi field office",
            "remote_level": "partial",
            "remote_emergency_reach": "sms",
            "spof_categories": ["single_supplier"],
            "spof_details": "Sole resin supplier",
        },
        industry="Manufacturing",
    )
    ctx = payload["additional_context"]
    assert ctx["travel_exposure"]["international_trips_monthly"] == 30
    assert ctx["travel_exposure"]["high_risk_trips_monthly"] == 5
    assert ctx["travel_exposure"]["high_risk_destinations"] == ["Mexico", "Kenya"]
    assert ctx["remote_workforce"]["remote_level"] == "partial"
    assert ctx["single_points_of_failure"]["categories"] == ["single_supplier"]


def test_contact_list_coerces_structured_contacts() -> None:
    payload = answers_to_intake(
        {
            "company_name": "Acme",
            "crisis_team_structure": [
                {
                    "name": "Jane Doe",
                    "country": "Germany",
                    "city": "Berlin",
                    "phone": "+49 30 12345",
                    "email": "jane@acme.com",
                }
            ],
        },
        industry="Manufacturing",
    )
    contacts = payload["additional_context"]["crisis_team_structure"]
    assert contacts[0]["name"] == "Jane Doe"
    assert contacts[0]["email"] == "jane@acme.com"


def test_contact_list_fields_use_structured_widget() -> None:
    schema = build_client_form_schema("Manufacturing")
    fields = {f["field_path"]: f for section in schema["sections"] for f in section["fields"]}
    assert fields["crisis_team_structure"]["type"] == "contact_list"
    assert fields["after_hours_escalation"]["type"] == "contact_list"


def test_legal_entities_uses_entity_list_widget() -> None:
    schema = build_client_form_schema("Humanitarian NGO")
    fields = {f["field_path"]: f for section in schema["sections"] for f in section["fields"]}
    assert fields["legal_entities"]["type"] == "entity_list"
    assert fields["legal_entities"]["role_options"]


def test_legal_entities_coerces_to_valid_list() -> None:
    payload = answers_to_intake(
        {
            "company_name": "Acme",
            "legal_entities": [
                {"name": "Acme GmbH", "country": "Germany", "role": "parent"},
                {"name": "Acme Mexico SA", "country": "Mexico", "role": "subsidiary"},
            ],
        },
        industry="Manufacturing",
    )
    intake = validate_intake_payload(payload)
    assert len(intake.legal_entities) == 2
    assert intake.legal_entities[0]["name"] == "Acme GmbH"


def test_legal_entities_legacy_dict_still_validates() -> None:
    intake = validate_intake_payload(
        {
            "company_name": "Acme",
            "industry": "Manufacturing",
            "legal_entities": {"notes": "Acme parent, US 501c3", "upload": None},
        }
    )
    assert isinstance(intake.legal_entities, list)
    assert intake.legal_entities[0]["name"] == "Acme parent, US 501c3"


def test_site_list_coerces_to_valid_intake() -> None:
    payload = answers_to_intake(
        {
            "company_name": "Acme",
            "sites": [
                {
                    "name": "Berlin HQ",
                    "country": "Germany",
                    "headcount": "120",
                    "primary_function": "headquarters",
                }
            ],
        },
        industry="Manufacturing",
    )
    intake = validate_intake_payload(payload)
    assert len(intake.sites) == 1
    assert intake.sites[0]["name"] == "Berlin HQ"
    assert intake.sites[0]["country"] == "Germany"
    assert intake.sites[0]["headcount"] == 120
