"""Client intake form schema derived from the requirements catalog."""

from __future__ import annotations

from typing import Any

from cmp.models.requirements import (
    Requirement,
    filter_requirements_for_industry,
    load_industry_modifier,
    load_requirements_catalog,
    load_yaml,
    knowledge_root,
)
from cmp.models.schemas import ClientIntake

TOP_LEVEL_FIELDS = frozenset(
    {
        "company_name",
        "industry",
        "employees",
        "countries",
        "headquarters_country",
        "organization_size",
        "crisis_program_maturity",
        "staffing_model",
        "legal_entities",
        "sites",
    }
)

DOMAIN_ORDER = [
    "org_profile",
    "operations_sites",
    "governance",
    "communications",
    "risk_bcp",
]

INDUSTRY_OPTIONS = [
    "Manufacturing",
    "Oil and Gas",
    "Energy",
    "Pharmaceutical",
    "Humanitarian NGO",
    "Professional Services",
    "Financial Services",
    "Technology",
    "Retail",
    "Other",
]

COUNTRY_OPTIONS = [
    "United States",
    "United Kingdom",
    "Canada",
    "Germany",
    "France",
    "Netherlands",
    "Spain",
    "Italy",
    "Ireland",
    "Belgium",
    "Switzerland",
    "Sweden",
    "Poland",
    "Mexico",
    "Brazil",
    "Thailand",
    "Japan",
    "Singapore",
    "Australia",
    "United Arab Emirates",
    "China",
    "India",
    "Kenya",
    "South Sudan",
    "South Africa",
    "Nigeria",
    "Colombia",
    "Other",
]

SIZE_OPTIONS = [
    {"value": "small", "label": "Small (under 50 employees)"},
    {"value": "medium", "label": "Medium (50–499 employees)"},
    {"value": "large", "label": "Large (500–4,999 employees)"},
    {"value": "enterprise", "label": "Enterprise (5,000+ employees)"},
]

MATURITY_OPTIONS = [
    {"value": "nascent", "label": "Nascent — little or no formal crisis program"},
    {"value": "developing", "label": "Developing — some plans or roles in place"},
    {"value": "established", "label": "Established — tested plans and exercise history"},
]

STAFFING_OPTIONS = [
    {"value": "lean", "label": "Lean — dual roles and limited dedicated staff"},
    {"value": "centralized", "label": "Centralized — crisis team primarily at HQ"},
    {"value": "distributed", "label": "Distributed — site/regional crisis leads"},
]

YES_NO_UNSURE = [
    {"value": "yes", "label": "Yes"},
    {"value": "no", "label": "No"},
    {"value": "unsure", "label": "Not sure / in progress"},
]

PUBLIC_LISTING_OPTIONS = [
    {"value": "private", "label": "Private company"},
    {"value": "public", "label": "Publicly listed"},
    {"value": "nonprofit", "label": "Non-profit / NGO"},
    {"value": "government", "label": "Government or public sector"},
    {"value": "other", "label": "Other"},
]

FREQUENCY_OPTIONS = [
    {"value": "none", "label": "None in the last 24 months"},
    {"value": "one", "label": "Once in the last 24 months"},
    {"value": "annual", "label": "At least annually"},
    {"value": "biannual", "label": "Twice per year or more"},
]

TRAVEL_VOLUME_OPTIONS = [
    {"value": "none", "label": "No regular business travel"},
    {"value": "low", "label": "Low (1–10 travelers per month)"},
    {"value": "medium", "label": "Medium (11–50 travelers per month)"},
    {"value": "high", "label": "High (50+ travelers per month)"},
]

WIDGET_OVERRIDES: dict[str, dict[str, Any]] = {
    "company_name": {"type": "text", "required": True},
    "industry": {"type": "select", "options": INDUSTRY_OPTIONS, "required": True},
    "employees": {"type": "number", "min": 1, "placeholder": "Total headcount globally"},
    "countries": {
        "type": "multiselect",
        "options": COUNTRY_OPTIONS,
        "required": True,
        "help": "Select all countries where you have employees, facilities, or material operations.",
    },
    "headquarters_country": {"type": "select", "options": COUNTRY_OPTIONS},
    "organization_size": {"type": "select", "options": SIZE_OPTIONS},
    "crisis_program_maturity": {"type": "select", "options": MATURITY_OPTIONS},
    "staffing_model": {"type": "select", "options": STAFFING_OPTIONS},
    "public_listing": {"type": "select", "options": PUBLIC_LISTING_OPTIONS},
    "existing_crisis_plan": {"type": "select", "options": YES_NO_UNSURE},
    "last_tabletop_exercise": {"type": "select", "options": FREQUENCY_OPTIONS},
    "tabletop_history": {"type": "textarea", "placeholder": "List exercises in the last 24 months, scenarios, and outcomes."},
    "post_incident_review": {"type": "select", "options": YES_NO_UNSURE},
    "travel_exposure": {"type": "select", "options": TRAVEL_VOLUME_OPTIONS},
    "remote_workforce": {
        "type": "select",
        "options": [
            {"value": "none", "label": "On-site only"},
            {"value": "partial", "label": "Hybrid / partial remote"},
            {"value": "majority", "label": "Majority remote"},
        ],
    },
    "dark_website": {"type": "select", "options": YES_NO_UNSURE},
    "mutual_aid": {"type": "select", "options": YES_NO_UNSURE},
    "cyber_incident_playbook": {"type": "select", "options": YES_NO_UNSURE},
    "pandemic_health_plan": {"type": "select", "options": YES_NO_UNSURE},
    "crisis_comms_training": {"type": "select", "options": FREQUENCY_OPTIONS},
    "emergency_drills_schedule": {"type": "select", "options": FREQUENCY_OPTIONS},
    "data_backup_recovery": {
        "type": "textarea",
        "placeholder": "Describe backup frequency, RPO/RTO targets, and last restore test.",
    },
    "legal_entities": {
        "type": "textarea",
        "placeholder": "List legal entities, country of incorporation, and role (e.g. parent, subsidiary).",
    },
    "sites": {
        "type": "textarea",
        "placeholder": "List major sites: name, country, approximate headcount, and primary function.",
    },
}


def _domain_labels() -> dict[str, str]:
    raw = load_yaml(knowledge_root() / "crisis_management" / "requirements_catalog.yaml")
    return {d["id"]: d["label"] for d in raw.get("domains", [])}


def _widget_for(req: Requirement) -> dict[str, Any]:
    override = dict(WIDGET_OVERRIDES.get(req.field_path, {}))
    widget_type = override.pop("type", "textarea")
    field: dict[str, Any] = {
        "field_path": req.field_path,
        "requirement_id": req.id,
        "label": req.label,
        "question": req.question_template,
        "why_it_matters": req.why_it_matters,
        "priority": req.priority.value,
        "type": widget_type,
        "required": override.pop("required", req.intake_required),
        "top_level": req.field_path in TOP_LEVEL_FIELDS,
    }
    if override:
        field.update(override)
    if widget_type == "textarea" and "placeholder" not in field:
        field["placeholder"] = "Provide as much detail as you can. Leave blank if not applicable."
    if req.industry_tags:
        field["industry_tags"] = req.industry_tags
    return field


def _req_domain(requirements: list[Requirement], field_path: str) -> str:
    for req in requirements:
        if req.field_path == field_path:
            return req.domain
    return "org_profile"


def build_client_form_schema(industry: str | None = None) -> dict[str, Any]:
    catalog = load_requirements_catalog()
    modifier = load_industry_modifier(industry) if industry else None
    requirements = filter_requirements_for_industry(catalog, modifier)

    seen: set[str] = set()
    fields: list[dict[str, Any]] = []
    for req in requirements:
        if req.field_path in seen:
            continue
        seen.add(req.field_path)
        fields.append(_widget_for(req))

    domain_labels = _domain_labels()
    sections: list[dict[str, Any]] = []
    for domain_id in DOMAIN_ORDER:
        section_fields = [f for f in fields if _req_domain(requirements, f["field_path"]) == domain_id]
        if not section_fields:
            continue
        sections.append(
            {
                "id": domain_id,
                "label": domain_labels.get(domain_id, domain_id),
                "fields": sorted(
                    section_fields,
                    key=lambda f: (not f["required"], f["label"]),
                ),
            }
        )

    return {
        "industry": industry,
        "field_count": len(fields),
        "sections": sections,
    }


def _coerce_value(field_path: str, raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, str):
        value = raw.strip()
        if not value:
            return None
        if field_path == "employees":
            try:
                return int(value)
            except ValueError:
                return value
        return value
    if isinstance(raw, list):
        cleaned = [str(item).strip() for item in raw if str(item).strip()]
        return cleaned or None
    return raw


def answers_to_intake(answers: dict[str, Any], industry: str | None = None) -> dict[str, Any]:
    intake: dict[str, Any] = {}
    additional: dict[str, Any] = {}

    for field_path, raw in answers.items():
        value = _coerce_value(field_path, raw)
        if value is None:
            continue
        if field_path in TOP_LEVEL_FIELDS:
            intake[field_path] = value
        else:
            additional[field_path] = value

    if industry and not intake.get("industry"):
        intake["industry"] = industry
    if additional:
        intake["additional_context"] = additional

    return intake


def validate_intake_payload(payload: dict[str, Any]) -> ClientIntake:
    return ClientIntake.model_validate(payload)
