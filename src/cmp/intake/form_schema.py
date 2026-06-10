"""Client intake form schema derived from the requirements catalog."""

from __future__ import annotations

from typing import Any

from cmp.intake.client_form_copy import client_field_copy, client_section_label
from cmp.intake.form_widgets import (
    COUNTRY_OPTIONS,
    COMPOUND_WIDGETS,
    CONTACT_LIST_FIELDS,
    contact_list_widget,
    field_visible_for_industry,
)
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

SIZE_OPTIONS = [
    {"value": "small", "label": "Small (under 50 employees)"},
    {"value": "medium", "label": "Medium (50–499 employees)"},
    {"value": "large", "label": "Large (500–4,999 employees)"},
    {"value": "enterprise", "label": "Enterprise (5,000+ employees)"},
]

MATURITY_OPTIONS = [
    {"value": "nascent", "label": "Just starting — little or no formal emergency program"},
    {"value": "developing", "label": "Partly in place — some plans, roles, or exercises exist"},
    {"value": "established", "label": "Well established — tested plans and regular exercises"},
]

STAFFING_OPTIONS = [
    {"value": "lean", "label": "Small team — people cover multiple emergency roles"},
    {"value": "centralized", "label": "Central team — leadership mainly at headquarters"},
    {"value": "distributed", "label": "Distributed — site or regional emergency leads"},
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

LEGAL_ENTITY_ROLE_OPTIONS = [
    {"value": "parent", "label": "Parent / headquarters company"},
    {"value": "subsidiary", "label": "Subsidiary"},
    {"value": "branch", "label": "Branch or local office"},
    {"value": "nonprofit", "label": "Registered charity / NGO"},
    {"value": "partnership", "label": "Partnership or joint venture"},
    {"value": "other", "label": "Other"},
]

WIDGET_OVERRIDES: dict[str, dict[str, Any]] = {
    "company_name": {"type": "text", "required": True},
    "industry": {"type": "select", "options": INDUSTRY_OPTIONS, "required": True},
    "employees": {"type": "number", "min": 1, "placeholder": "Total headcount globally"},
    "countries": {
        "type": "country_multiselect",
        "options": COUNTRY_OPTIONS,
        "required": True,
        "help": "Select every country where you have staff, offices, warehouses, or major operations.",
    },
    "headquarters_country": {
        "type": "select",
        "options": COUNTRY_OPTIONS,
        "help": "The country where your main headquarters or legal home office is located.",
    },
    "organization_size": {"type": "select", "options": SIZE_OPTIONS},
    "crisis_program_maturity": {"type": "select", "options": MATURITY_OPTIONS},
    "staffing_model": {"type": "select", "options": STAFFING_OPTIONS},
    "ot_ics_security": {
        "type": "compound",
        "parts": [
            {
                "name": "ot_segmented",
                "label": "Are operational control systems kept separate from office IT networks?",
                "type": "select",
                "options": [
                    {"value": "yes", "label": "Yes — clearly separated"},
                    {"value": "partial", "label": "Partly separated"},
                    {"value": "no", "label": "No / shared network"},
                    {"value": "unsure", "label": "Not sure"},
                ],
            },
            {
                "name": "ot_security_details",
                "label": "Describe protections, monitoring, and who responds to OT incidents",
                "type": "textarea",
                "placeholder": "Asset inventory, firewalls, incident coordination with IT security",
            },
        ],
        "help": "Only applies if you operate plant, pipeline, or facility control systems.",
    },
    "existing_crisis_plan": {"type": "select", "options": YES_NO_UNSURE},
    "last_tabletop_exercise": {"type": "select", "options": FREQUENCY_OPTIONS},
    "tabletop_history": {"type": "textarea", "placeholder": "List practice exercises from the last two years, scenarios used, and key takeaways."},
    "post_incident_review": {"type": "select", "options": YES_NO_UNSURE},
    "dark_website": {"type": "select", "options": YES_NO_UNSURE},
    "mutual_aid": {"type": "select", "options": YES_NO_UNSURE},
    "cyber_incident_playbook": {"type": "select", "options": YES_NO_UNSURE},
    "pandemic_health_plan": {"type": "select", "options": YES_NO_UNSURE},
    "crisis_comms_training": {"type": "select", "options": FREQUENCY_OPTIONS},
    "emergency_drills_schedule": {"type": "select", "options": FREQUENCY_OPTIONS},
    "data_backup_recovery": {
        "type": "textarea",
        "placeholder": "How often backups run, how quickly systems must be restored, and when you last tested a restore.",
    },
    "legal_entities": {
        "type": "entity_list",
        "help": "Add each legal company in your group. Example: parent charity in the UK, country office registered locally.",
        "role_options": LEGAL_ENTITY_ROLE_OPTIONS,
        "file_part": {
            "name": "legal_entities_file",
            "label": "Or upload an org chart or entity list (optional)",
            "type": "file",
            "accept": ".pdf,.docx,.txt,.csv,.json",
        },
    },
    "sites": {
        "type": "site_list",
        "help": "Add each major office, plant, warehouse, or field hub. You can also upload a site list file.",
        "file_part": {
            "name": "sites_file",
            "label": "Upload site list (optional)",
            "type": "file",
            "accept": ".pdf,.docx,.txt,.csv,.xlsx,.json",
        },
    },
}

# Merge compound widget definitions from form_widgets.
for field_path, widget in COMPOUND_WIDGETS.items():
    WIDGET_OVERRIDES.setdefault(field_path, widget)


def _domain_labels() -> dict[str, str]:
    raw = load_yaml(knowledge_root() / "crisis_management" / "requirements_catalog.yaml")
    return {d["id"]: d["label"] for d in raw.get("domains", [])}


def _widget_for(req: Requirement) -> dict[str, Any]:
    override = dict(WIDGET_OVERRIDES.get(req.field_path, {}))
    widget_type = override.pop("type", "select" if req.intake_required else "textarea")
    copy = client_field_copy(req)

    field: dict[str, Any] = {
        "field_path": req.field_path,
        "requirement_id": req.id,
        "label": copy["label"],
        "question": copy["question"],
        "help": override.pop("help", None) or copy.get("help") or "",
        "priority": req.priority.value,
        "priority_label": copy["priority_label"],
        "type": widget_type,
        "required": override.pop("required", req.intake_required),
        "top_level": req.field_path in TOP_LEVEL_FIELDS,
    }
    if override:
        field.update(override)
    if req.field_path in CONTACT_LIST_FIELDS:
        field.update(contact_list_widget())
    if widget_type == "site_list" or widget_type == "entity_list":
        field["country_options"] = COUNTRY_OPTIONS
    if widget_type == "textarea" and "placeholder" not in field:
        field["placeholder"] = "Leave blank if not applicable."
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
        if not field_visible_for_industry(req.field_path, industry):
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
                "label": client_section_label(domain_id, domain_labels),
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


def _coerce_scalar(field_path: str, raw: Any) -> Any:
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
        if field_path in ("travel_international_trips", "travel_high_risk_trips"):
            try:
                return int(value)
            except ValueError:
                return value
        return value
    if isinstance(raw, list):
        cleaned = [str(item).strip() for item in raw if str(item).strip()]
        return cleaned or None
    return raw


def _coerce_sites(raw: Any) -> list[dict[str, Any]] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        return [{"name": "Site details (free text)", "notes": text}]
    if not isinstance(raw, list):
        return None
    sites: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        site: dict[str, Any] = {"name": name}
        country = str(item.get("country") or "").strip()
        if country:
            site["country"] = country
        headcount = item.get("headcount")
        if headcount not in (None, ""):
            try:
                site["headcount"] = int(headcount)
            except (TypeError, ValueError):
                site["headcount"] = headcount
        function = item.get("primary_function") or item.get("function")
        if function:
            site["primary_function"] = str(function).strip()
        sites.append(site)
    return sites or None


def _coerce_legal_entities(raw: Any) -> list[dict[str, Any]] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        notes = str(raw.get("notes") or "").strip()
        if not notes:
            return None
        return [{"name": notes, "role": "other"}]
    if not isinstance(raw, list):
        return None
    entities: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        entity: dict[str, Any] = {"name": name}
        country = str(item.get("country") or "").strip()
        if country:
            entity["country"] = country
        role = str(item.get("role") or "").strip()
        if role:
            entity["role"] = role
        entities.append(entity)
    return entities or None


def _coerce_contacts(raw: Any) -> list[dict[str, Any]] | str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        text = raw.strip()
        return text if text else None
    if not isinstance(raw, list):
        return None
    contacts: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        contact: dict[str, Any] = {"name": name}
        for key in ("country", "city", "phone", "email"):
            value = str(item.get(key) or "").strip()
            if value:
                contact[key] = value
        contacts.append(contact)
    return contacts or None


def _merge_compound_fields(answers: dict[str, Any]) -> dict[str, Any]:
    merged = dict(answers)

    if any(
        key in merged
        for key in (
            "travel_international_trips",
            "travel_high_risk_trips",
            "travel_high_risk_destinations",
            "travel_destinations_notes",
        )
    ):
        merged["travel_exposure"] = {
            "international_trips_monthly": _coerce_scalar(
                "travel_international_trips", merged.pop("travel_international_trips", None)
            ),
            "high_risk_trips_monthly": _coerce_scalar(
                "travel_high_risk_trips", merged.pop("travel_high_risk_trips", None)
            ),
            "high_risk_destinations": merged.pop("travel_high_risk_destinations", []),
            "notes": merged.pop("travel_destinations_notes", None),
        }

    if any(key in merged for key in ("remote_level", "remote_emergency_reach", "remote_emergency_notes")):
        merged["remote_workforce"] = {
            "remote_level": merged.pop("remote_level", None),
            "emergency_reach": merged.pop("remote_emergency_reach", None),
            "notes": merged.pop("remote_emergency_notes", None),
        }

    if any(key in merged for key in ("spof_categories", "spof_details")):
        merged["single_points_of_failure"] = {
            "categories": merged.pop("spof_categories", []),
            "details": merged.pop("spof_details", None),
        }

    if any(key in merged for key in ("utility_risks", "utility_details")):
        merged["utilities_dependencies"] = {
            "services": merged.pop("utility_risks", []),
            "details": merged.pop("utility_details", None),
        }

    if any(key in merged for key in ("decision_types", "decision_holders")):
        merged["decision_authorities"] = {
            "decision_types": merged.pop("decision_types", []),
            "holders": merged.pop("decision_holders", None),
        }

    if any(key in merged for key in ("business_model_summary", "revenue_dependency")):
        merged["business_model"] = {
            "summary": merged.pop("business_model_summary", None),
            "revenue_dependency": merged.pop("revenue_dependency", None),
        }

    if any(key in merged for key in ("key_customers_exist", "key_customers_list")):
        merged["key_customers"] = {
            "concentrated": merged.pop("key_customers_exist", None),
            "priority_contacts": merged.pop("key_customers_list", None),
        }

    if any(key in merged for key in ("ot_segmented", "ot_security_details")):
        merged["ot_ics_security"] = {
            "segmented": merged.pop("ot_segmented", None),
            "details": merged.pop("ot_security_details", None),
        }

    return merged


def answers_to_intake(answers: dict[str, Any], industry: str | None = None) -> dict[str, Any]:
    merged_answers = _merge_compound_fields(answers)
    intake: dict[str, Any] = {}
    additional: dict[str, Any] = {}

    for field_path, raw in merged_answers.items():
        if field_path == "sites":
            value = _coerce_sites(raw)
        elif field_path == "legal_entities":
            value = _coerce_legal_entities(raw)
        elif field_path in CONTACT_LIST_FIELDS:
            value = _coerce_contacts(raw)
        elif field_path.endswith("_file"):
            if raw:
                additional[field_path] = raw
            continue
        else:
            value = _coerce_scalar(field_path, raw)

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
