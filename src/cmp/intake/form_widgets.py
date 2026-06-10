"""Widget definitions and industry visibility rules for the client intake form."""

from __future__ import annotations

from typing import Any

COUNTRY_OPTIONS = [
    "Afghanistan",
    "Australia",
    "Austria",
    "Belgium",
    "Brazil",
    "Canada",
    "China",
    "Colombia",
    "Dominica",
    "Denmark",
    "Egypt",
    "Ethiopia",
    "Finland",
    "France",
    "Germany",
    "India",
    "Indonesia",
    "Ireland",
    "Israel",
    "Italy",
    "Japan",
    "Kenya",
    "Mexico",
    "Netherlands",
    "New Zealand",
    "Nigeria",
    "Norway",
    "Pakistan",
    "Philippines",
    "Poland",
    "Singapore",
    "South Africa",
    "South Korea",
    "South Sudan",
    "Spain",
    "Sweden",
    "Switzerland",
    "Thailand",
    "Turkey",
    "Ukraine",
    "United Arab Emirates",
    "United Kingdom",
    "United States",
    "Vietnam",
    "Other",
]

INDUSTRIAL_INDUSTRIES = frozenset(
    {"Manufacturing", "Oil and Gas", "Energy", "Pharmaceutical"}
)

# Fields hidden for specific industries (client form only).
EXCLUDE_FOR_INDUSTRY: dict[str, frozenset[str]] = {
    "Humanitarian NGO": frozenset(
        {
            "business_model",
            "key_customers",
            "public_listing",
            "investor_relations",
            "product_recall_capability",
            "gxp_compliance",
            "pharmacovigilance_contacts",
            "quality_crisis_authority",
            "cold_chain_integrity",
            "production_continuity",
            "pipeline_infrastructure",
            "process_safety_management",
            "major_accident_hazard",
            "environmental_release_energy",
            "energy_regulatory_contacts",
            "industrial_accident_scenarios",
            "environmental_liability",
            "labor_industrial_relations",
        }
    ),
}

# Fields shown only for listed industries (client form only).
ONLY_FOR_INDUSTRIES: dict[str, frozenset[str]] = {
    "ot_ics_security": INDUSTRIAL_INDUSTRIES,
    "ot_ics_environment": INDUSTRIAL_INDUSTRIES,
    "ot_ics_backup_recovery": INDUSTRIAL_INDUSTRIES,
    "production_continuity": frozenset({"Manufacturing", "Pharmaceutical"}),
    "pipeline_infrastructure": frozenset({"Oil and Gas", "Energy"}),
    "process_safety_management": frozenset({"Oil and Gas", "Energy"}),
    "major_accident_hazard": frozenset({"Oil and Gas", "Energy"}),
    "environmental_release_energy": frozenset({"Oil and Gas", "Energy"}),
    "energy_regulatory_contacts": frozenset({"Oil and Gas", "Energy"}),
    "cold_chain_integrity": frozenset({"Pharmaceutical"}),
    "product_recall_capability": frozenset({"Pharmaceutical"}),
    "gxp_compliance": frozenset({"Pharmaceutical"}),
    "pharmacovigilance_contacts": frozenset({"Pharmaceutical"}),
    "quality_crisis_authority": frozenset({"Pharmaceutical"}),
    "local_partner_vetting": frozenset({"Humanitarian NGO"}),
    "field_team_security": frozenset({"Humanitarian NGO"}),
    "kidnap_hostage_response": frozenset({"Humanitarian NGO"}),
    "duty_of_care_travelers": frozenset({"Humanitarian NGO"}),
    "donor_stakeholder_comms": frozenset({"Humanitarian NGO"}),
}

CONTACT_LIST_FIELDS = frozenset(
    {
        "site_activation_contacts",
        "after_hours_escalation",
        "legal_counsel_contacts",
        "family_liaison",
        "csr_esg_contacts",
        "energy_regulatory_contacts",
        "pharmacovigilance_contacts",
        "union_stakeholders",
        "investor_relations",
        "crisis_team_structure",
    }
)

TRAVEL_VOLUME_OPTIONS = [
    {"value": "none", "label": "No regular international travel"},
    {"value": "low", "label": "Low (1–10 people per month)"},
    {"value": "medium", "label": "Medium (11–50 people per month)"},
    {"value": "high", "label": "High (more than 50 people per month)"},
]

REMOTE_LEVEL_OPTIONS = [
    {"value": "none", "label": "Almost everyone works on-site"},
    {"value": "partial", "label": "Hybrid — some remote, some on-site"},
    {"value": "majority", "label": "Most people work remotely"},
]

REMOTE_REACH_OPTIONS = [
    {"value": "phone_tree", "label": "Phone call tree or direct manager calls"},
    {"value": "sms", "label": "SMS or mass notification system"},
    {"value": "email", "label": "Email"},
    {"value": "collaboration_app", "label": "Teams, Slack, or similar app"},
    {"value": "other", "label": "Other method"},
    {"value": "unsure", "label": "Not sure / not defined yet"},
]

SPOF_CHECKLIST = [
    {"value": "single_site", "label": "One location where too much work is concentrated"},
    {"value": "single_supplier", "label": "One supplier we cannot replace quickly"},
    {"value": "single_system", "label": "One IT or operations system everything depends on"},
    {"value": "single_person", "label": "One person with unique knowledge or authority"},
    {"value": "single_utility", "label": "One power, water, or telecom provider with no backup"},
    {"value": "none_identified", "label": "None identified yet"},
]

UTILITY_CHECKLIST = [
    {"value": "electricity", "label": "Electricity / power"},
    {"value": "water", "label": "Water supply"},
    {"value": "internet", "label": "Internet and phones"},
    {"value": "gas", "label": "Gas or fuel supply"},
    {"value": "hvac", "label": "Heating, cooling, or ventilation"},
    {"value": "other", "label": "Other essential service"},
]

DECISION_CHECKLIST = [
    {"value": "evacuation", "label": "Approve evacuation or shelter-in-place"},
    {"value": "shutdown", "label": "Stop operations or close a site"},
    {"value": "media", "label": "Approve public or media statements"},
    {"value": "regulators", "label": "Notify government or regulators"},
    {"value": "spending", "label": "Approve emergency spending"},
    {"value": "travel", "label": "Cancel travel or recall people from abroad"},
]

COMPOUND_WIDGETS: dict[str, dict[str, Any]] = {
    "travel_exposure": {
        "type": "compound",
        "parts": [
            {
                "name": "travel_international_trips",
                "label": "How many international trips does your organization take per month (all employees combined)?",
                "type": "number",
                "placeholder": "e.g. 25",
                "min": 0,
            },
            {
                "name": "travel_high_risk_trips",
                "label": "How many of those trips are to high-risk destinations?",
                "type": "number",
                "placeholder": "e.g. 5",
                "min": 0,
            },
            {
                "name": "travel_high_risk_destinations",
                "label": "What are those high-risk destinations?",
                "type": "country_multiselect",
                "options": COUNTRY_OPTIONS,
            },
            {
                "name": "travel_destinations_notes",
                "label": "Other destinations or details (optional)",
                "type": "text",
                "placeholder": "e.g. specific cities or remote field locations",
            },
        ],
        "help": "Count all business travel abroad. High-risk means places with elevated security, health, or political concerns.",
    },
    "remote_workforce": {
        "type": "compound",
        "parts": [
            {
                "name": "remote_level",
                "label": "How much of your workforce is remote or hybrid?",
                "type": "select",
                "options": REMOTE_LEVEL_OPTIONS,
            },
            {
                "name": "remote_emergency_reach",
                "label": "How would you reach remote workers during a site emergency?",
                "type": "select",
                "options": REMOTE_REACH_OPTIONS,
            },
            {
                "name": "remote_emergency_notes",
                "label": "Additional details (optional)",
                "type": "text",
                "placeholder": "e.g. manager call lists, app used, gaps",
            },
        ],
    },
    "single_points_of_failure": {
        "type": "compound",
        "parts": [
            {
                "name": "spof_categories",
                "label": "Which of these apply to your organization?",
                "type": "checklist",
                "options": SPOF_CHECKLIST,
            },
            {
                "name": "spof_details",
                "label": "Name the location, supplier, system, or person (if known)",
                "type": "textarea",
                "placeholder": "Example: Only one datacenter in Frankfurt; sole supplier for component X",
            },
        ],
        "help": (
            "A single point of failure is anything that, if it stopped working, would seriously "
            "disrupt your organization with no quick backup."
        ),
    },
    "utilities_dependencies": {
        "type": "compound",
        "parts": [
            {
                "name": "utility_risks",
                "label": "Which essential services would be hardest to replace quickly if they failed?",
                "type": "checklist",
                "options": UTILITY_CHECKLIST,
            },
            {
                "name": "utility_details",
                "label": "Which locations are most affected, and do you have backups?",
                "type": "textarea",
                "placeholder": "Example: Plant A relies on one power feed; generator on site for 48 hours",
            },
        ],
        "help": "Think about power, water, internet, fuel, and heating/cooling at your main locations.",
    },
    "decision_authorities": {
        "type": "compound",
        "parts": [
            {
                "name": "decision_types",
                "label": "Which types of emergency decisions need a clear owner?",
                "type": "checklist",
                "options": DECISION_CHECKLIST,
            },
            {
                "name": "decision_holders",
                "label": "Who can make these decisions (names or roles)?",
                "type": "textarea",
                "placeholder": "Example: COO can approve site closure; CEO approves media statements",
            },
        ],
    },
    "business_model": {
        "type": "compound",
        "parts": [
            {
                "name": "business_model_summary",
                "label": "What does your organization do and who do you serve?",
                "type": "textarea",
                "placeholder": "Products, services, customers, or communities served",
            },
            {
                "name": "revenue_dependency",
                "label": "Do a few customers or funders represent most of your income?",
                "type": "select",
                "options": [
                    {"value": "no", "label": "No — income is broadly spread"},
                    {"value": "some", "label": "Some concentration"},
                    {"value": "high", "label": "Yes — a few customers/funders are critical"},
                    {"value": "unsure", "label": "Not sure"},
                ],
            },
        ],
    },
    "key_customers": {
        "type": "compound",
        "parts": [
            {
                "name": "key_customers_exist",
                "label": "Do a few customers represent a large share of revenue?",
                "type": "select",
                "options": [
                    {"value": "no", "label": "No"},
                    {"value": "yes", "label": "Yes"},
                    {"value": "unsure", "label": "Not sure"},
                ],
            },
            {
                "name": "key_customers_list",
                "label": "If yes, who should be notified first during a major disruption?",
                "type": "textarea",
                "placeholder": "Customer names or categories and contact approach",
            },
        ],
    },
}


def contact_list_widget() -> dict[str, Any]:
    return {
        "type": "contact_list",
        "country_options": COUNTRY_OPTIONS,
        "help": "Add one row per person or role. Include backup contacts where possible.",
    }


def field_visible_for_industry(field_path: str, industry: str | None) -> bool:
    if industry:
        excluded = EXCLUDE_FOR_INDUSTRY.get(industry, frozenset())
        if field_path in excluded:
            return False
        only = ONLY_FOR_INDUSTRIES.get(field_path)
        if only is not None and industry not in only:
            return False
    elif field_path in ONLY_FOR_INDUSTRIES:
        return False
    return True


def widget_override_for(field_path: str) -> dict[str, Any] | None:
    if field_path in COMPOUND_WIDGETS:
        return dict(COMPOUND_WIDGETS[field_path])
    return None
