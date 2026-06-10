"""Generate plain-language client intake copy from the requirements catalog."""

from __future__ import annotations

from pathlib import Path

import yaml

from cmp.intake.client_form_copy import CLIENT_DOMAIN_LABELS, clientize_text
from cmp.models.requirements import load_requirements_catalog, repo_root

CUSTOM = {
    "company_name": {
        "label": "Your organization's legal name",
        "question": "What is your organization's full legal name?",
        "help": "Include parent company or subsidiary names if relevant.",
    },
    "industry": {
        "label": "Main type of business",
        "question": "What industry best describes your organization?",
    },
    "employees": {
        "label": "Total number of people",
        "question": "How many employees and contractors do you have in total (worldwide)?",
    },
    "countries": {
        "label": "Countries where you operate",
        "question": "Select every country where you have employees, offices, warehouses, or major operations.",
        "help": "Use Ctrl (Windows) or Cmd (Mac) to select more than one country.",
    },
    "headquarters_country": {
        "label": "Headquarters country",
        "question": "In which country is your organization headquartered or legally registered?",
        "help": "This is usually where your main office or parent company is domiciled.",
    },
    "sites": {
        "label": "Your locations",
        "question": "Add each major office, plant, warehouse, or field hub.",
        "help": "For each location, provide a name, country, approximate headcount, and main activity. You can add rows or upload a site list file.",
    },
    "business_model": {
        "label": "What your organization does",
        "question": "Briefly describe your products or services, who you serve, and whether income depends on a few customers or funders.",
        "help": "This helps us understand what must be protected during a disruption.",
    },
    "key_customers": {
        "label": "Important customers or clients",
        "question": "Do a few customers represent a large share of your revenue? Who should be notified first during a major disruption?",
        "help": "Skip or answer 'No' if this does not apply to your organization.",
    },
    "travel_exposure": {
        "label": "Employee travel",
        "question": "How many international trips your staff take each month, how many go to high-risk places, and where those places are.",
        "help": "Count all business travel abroad. High-risk means elevated security, health, or political concerns.",
    },
    "remote_workforce": {
        "label": "Remote and hybrid workers",
        "question": "How much of your workforce works remotely or hybrid, and how would you reach them during a site-level emergency?",
    },
    "single_points_of_failure": {
        "label": "Operational weak points",
        "question": "What would seriously disrupt your organization if it stopped working with no quick backup?",
        "help": "Examples: one datacenter, one supplier, one person with unique authority, or one utility feed.",
    },
    "utilities_dependencies": {
        "label": "Essential services at your locations",
        "question": "At your main locations, which essential services (power, water, internet, fuel) would be hardest to replace if they failed?",
        "help": "Tell us which sites are affected and whether you have backup generators, tanks, or alternate providers.",
    },
    "decision_authorities": {
        "label": "Who can make major emergency decisions",
        "question": "For serious incidents, who can approve evacuation, stopping operations, public statements, regulator notification, and emergency spending?",
        "help": "List names or roles — clarity here prevents delays during a crisis.",
    },
    "crisis_team_structure": {
        "label": "Emergency leadership team",
        "question": "Who leads your organization during a serious emergency? List roles, names, and backup contacts.",
    },
    "existing_crisis_plan": {
        "label": "Existing emergency or crisis plan",
        "question": "Do you have a written crisis or emergency plan today? When was it last updated?",
    },
    "last_tabletop_exercise": {
        "label": "Last crisis practice exercise",
        "question": "When did you last run a crisis practice exercise or simulation? What was practiced?",
    },
    "tabletop_history": {
        "label": "Recent crisis practice exercises",
        "question": "List any crisis practice exercises from the last two years, what you practiced, and what you learned.",
    },
    "existing_bcp": {
        "label": "Business continuity plans",
        "question": "Do you have plans for keeping critical work going if a site or system is unavailable?",
    },
    "ot_ics_environment": {
        "label": "Factory or plant control systems",
        "question": "Do you use industrial control or plant automation systems? Who can authorize an emergency shutdown?",
    },
    "ot_ics_security": {
        "label": "Security for operational technology (OT)",
        "question": "How are plant, facility, or pipeline control systems protected and kept separate from office IT networks?",
        "help": "Only applies if you operate industrial control or automation systems.",
    },
    "dark_website": {
        "label": "Standby crisis website",
        "question": "Do you have a pre-built website or web page ready to publish during a major public incident?",
    },
    "data_backup_recovery": {
        "label": "Data backup and recovery",
        "question": "How often are critical systems backed up, and when did you last test restoring data?",
    },
    "production_continuity": {
        "label": "How quickly production must resume",
        "question": "If production stopped, how quickly must each major line or site be running again?",
    },
    "crisis_program_maturity": {
        "label": "How developed your emergency program is",
        "question": "How would you describe your current crisis preparedness?",
    },
    "staffing_model": {
        "label": "How crisis responsibilities are organized",
        "question": "Is emergency leadership handled by a small shared team, a central headquarters team, or regional and site leads?",
    },
    "organization_size": {
        "label": "Organization size",
        "question": "Which size category best fits your organization?",
    },
    "legal_entities": {
        "label": "Companies in your group",
        "question": "List each legal company in your group, where it is registered, and its role (parent, subsidiary, branch, etc.).",
        "help": "Use one row per company. You can also upload an org chart or entity list file.",
    },
    "critical_functions": {
        "label": "Most important work that must continue",
        "question": "Which activities would cause serious harm if stopped for 4 hours, 24 hours, or 3 days?",
        "help": "This helps prioritize recovery during a disruption.",
    },
    "site_activation_contacts": {
        "label": "Site emergency contacts",
        "question": "For each major location, who is the main and backup emergency contact, including after-hours numbers?",
    },
    "crisis_activation_criteria": {
        "label": "When you declare a formal emergency",
        "question": "What situations require senior leaders to take charge (for example deaths, serious injuries, major outages, or media attention)?",
    },
    "escalation_matrix": {
        "label": "Who to notify and when",
        "question": "Who gets notified as an incident gets more serious, and how are they contacted?",
    },
    "crisis_levels": {
        "label": "How you classify incident severity",
        "question": "How do you rank incidents from minor to severe today?",
    },
    "after_hours_escalation": {
        "label": "After-hours emergency contacts",
        "question": "Who can be reached outside normal business hours during an emergency, and how?",
    },
    "spokesperson_policy": {
        "label": "Who may speak publicly",
        "question": "Who is allowed to speak to employees, media, customers, or regulators during an incident?",
    },
    "family_liaison": {
        "label": "Contact with families after serious harm",
        "question": "Is there a named person and process for contacting families after a death, serious injury, or missing person?",
    },
    "cyber_incident_playbook": {
        "label": "Cyber attack response plan",
        "question": "Do you have a written plan for cyber attacks? Who decides when it becomes a company-wide emergency?",
    },
    "risk_register": {
        "label": "Major risks you track",
        "question": "Do you maintain a list of major risks? What are the top concerns for the next year?",
    },
    "mutual_aid": {
        "label": "Emergency help from neighboring organizations",
        "question": "Do you have agreements to receive emergency help from nearby companies or industry peers?",
    },
    "regulator_notification_templates": {
        "label": "Prepared messages for regulators",
        "question": "Do you have pre-approved messages for notifying government authorities after common incidents?",
    },
    "pharmacovigilance_contacts": {
        "label": "Drug safety reporting contacts",
        "question": "Who handles reporting adverse drug events to health authorities?",
    },
    "process_safety_management": {
        "label": "Major hazard safety program",
        "question": "Describe your program for preventing major industrial accidents and how changes to hazardous processes are managed.",
    },
    "field_team_security": {
        "label": "Security for staff working in the field",
        "question": "How do you keep field staff safe in higher-risk areas, including training and threat monitoring?",
    },
    "kidnap_hostage_response": {
        "label": "Kidnap or hostage response plan",
        "question": "Do you have a plan for kidnapping or hostage situations, including insurance if applicable?",
    },
    "cyber_physical_incidents": {
        "label": "Cyber attacks that affect physical operations",
        "question": "Have you planned for cyber attacks that could shut down plant systems or affect safety equipment?",
    },
    "traveler_tracking": {
        "label": "Tracking employees who are traveling",
        "question": "How do you know where traveling employees are and confirm they are safe during an overseas incident?",
    },
    "critical_third_parties": {
        "label": "Outside organizations you depend on",
        "question": "Which outside providers are critical to your operations, and where would failure hurt you most?",
    },
}


def soften_question(question: str) -> str:
    for src, dst in (
        ("Provide ", "Please share "),
        ("Describe ", "Please describe "),
        ("List ", "Please list "),
        ("Briefly describe ", "In a few sentences, describe "),
    ):
        if question.startswith(src):
            return dst + question[len(src) :]
    return question


def soften_help(help_text: str) -> str:
    text = clientize_text(help_text)
    text = text.replace("24/7", "around the clock")
    text = text.replace("comms ", "communications ")
    return text


def main() -> None:
    fields: dict[str, dict[str, str]] = {}
    seen: set[str] = set()
    for req in load_requirements_catalog():
        if req.field_path in seen:
            continue
        seen.add(req.field_path)
        if req.field_path in CUSTOM:
            fields[req.field_path] = CUSTOM[req.field_path]
            continue
        fields[req.field_path] = {
            "label": clientize_text(req.label),
            "question": soften_question(clientize_text(req.question_template)),
            "help": soften_help(req.why_it_matters),
        }

    path = repo_root() / "knowledge" / "crisis_management" / "client_intake_copy.yaml"
    path.write_text(
        yaml.dump({"domains": CLIENT_DOMAIN_LABELS, "fields": fields}, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print(f"Wrote {len(fields)} fields to {path}")


if __name__ == "__main__":
    main()
