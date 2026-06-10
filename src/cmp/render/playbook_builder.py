"""Build role-based crisis playbooks from governance and risk data."""

from __future__ import annotations

import re

from cmp.models.schemas import (
    GovernanceOutput,
    PlaybookBundle,
    PlaybookRole,
    ProcedureOutput,
    RiskItem,
    RiskProfileOutput,
    RoleAction,
)

# Keywords in risk titles → role name fragments to activate (matched against CMT roster).
RISK_ROLE_HINTS: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("cyber", "ot", "ics", "ransomware", "it "), ("Cyber", "IT")),
    (("media", "reputation", "recall", "quality defect"), ("Communications", "People")),
    (("regulatory", "environmental", "spill", "enforcement"), ("Legal", "Compliance")),
    (("labor", "strike", "workforce", "casualty", "injur", "fatal"), ("HR", "People", "Operations")),
    (("travel", "kidnap", "field", "security"), ("Operations", "People")),
    (("supply", "production", "plant", "site", "natural", "flood", "earthquake", "hurricane"), ("Operations",)),
    (("board", "executive", "multi-site", "cross-border"), ("Crisis Director", "Crisis Lead")),
]

ROLE_PROFILES: dict[str, dict[str, object]] = {
    "crisis": {
        "match": ("crisis director", "crisis lead"),
        "activates_when": "Level 3–4 crises, or when any incident threatens life safety, regulatory action, or enterprise continuity.",
        "purpose": "Own the overall response: set objectives, allocate resources, and decide when to stand down.",
        "first_15": (
            "Confirm the situation with the site or programme lead. Declare the crisis level and convene "
            "the activated roles on the crisis bridge. Assign a scribe and establish a decision log."
        ),
        "during": (
            "Issue situation updates on a fixed cadence. Resolve conflicts between workstreams. Approve "
            "external statements, regulator contact, and major operational decisions."
        ),
        "decisions": ["Crisis activation and level changes", "Major resource commitments", "Stand-down"],
        "coordinates": ["All activated CMT roles", "CEO or board liaison at Level 4"],
        "stand_down": "Formally close the crisis when objectives are met and no further CMT coordination is required.",
    },
    "operations": {
        "match": ("operations", "safety"),
        "activates_when": "Any incident affecting sites, assets, personnel safety, or production continuity (typically Level 2+).",
        "purpose": "Protect people and assets, stabilise operations, and advise on shutdown or restart.",
        "first_15": (
            "Account for all personnel in the affected area. Secure the scene and liaise with emergency services. "
            "Report facts only — what happened, who is affected, what is contained — to the crisis lead."
        ),
        "during": (
            "Maintain a live operational picture: site status, production impact, utilities, and recovery needs. "
            "Recommend operational decisions; implement those approved by the crisis lead."
        ),
        "decisions": ["Evacuation or shelter-in-place recommendation", "Operational shutdown scope"],
        "coordinates": ["Site or programme leads", "IT/Cyber lead if systems involved", "Legal for regulatory incidents"],
        "stand_down": "Confirm sites are stable and hand operational recovery to line management.",
    },
    "communications": {
        "match": ("communications", "people"),
        "activates_when": "Level 2+ when employees, families, media, donors, or customers need accurate information.",
        "purpose": "Ensure one voice: internal updates, external statements, and monitoring of public narrative.",
        "first_15": (
            "Issue a brief internal holding message to affected staff. Identify the authorised spokesperson. "
            "Begin monitoring media and social channels for emerging narratives."
        ),
        "during": (
            "Draft and clear statements with the crisis lead. Coordinate employee, family, and stakeholder updates. "
            "Log all outbound communications."
        ),
        "decisions": ["Approved holding statements", "Employee notification content"],
        "coordinates": ["Crisis lead", "Legal before regulator or media contact", "HR for family liaison"],
        "stand_down": "Publish final internal summary and archive communications log.",
    },
    "legal": {
        "match": ("legal", "compliance", "insurance"),
        "activates_when": "Regulatory interest, legal exposure, insurance notification, or formal investigation (typically Level 2+).",
        "purpose": "Manage regulatory, legal, and insurance obligations without compromising the operational response.",
        "first_15": (
            "Advise on immediate regulatory notification deadlines. Preserve records and restrict document destruction. "
            "Contact insurers or brokers if policy conditions require prompt notice."
        ),
        "during": (
            "Coordinate regulator correspondence through approved channels. Support root-cause and evidence preservation. "
            "Review external statements for legal risk."
        ),
        "decisions": ["Regulatory notification timing and content", "Investigation scope"],
        "coordinates": ["Crisis lead", "Communications", "Operations for factual inputs"],
        "stand_down": "Confirm regulatory filings complete and transition to any formal investigation.",
    },
    "hr": {
        "match": ("hr", "people"),
        "activates_when": "Injuries, fatalities, missing persons, family inquiries, or widespread workforce welfare concerns.",
        "purpose": "Support affected people and families with care, accuracy, and dignity.",
        "first_15": (
            "Activate casualty tracking and family liaison protocols. Ensure next-of-kin are informed through "
            "designated contacts only — not via social media or unverified channels."
        ),
        "during": (
            "Maintain confidential welfare tracking. Coordinate counselling or EAP resources. Brief leadership on "
            "workforce morale and absenteeism risk."
        ),
        "decisions": ["Family notification sequencing", "Employee support measures"],
        "coordinates": ["Communications", "Operations for site access", "Legal for privacy"],
        "stand_down": "Transfer ongoing welfare support to HR line management.",
    },
    "it": {
        "match": ("it", "cyber"),
        "activates_when": "Cyber incidents, OT/ICS anomalies, or technology outages that threaten safety or operations.",
        "purpose": "Contain technology threats, restore critical systems, and coordinate with operations on safe states.",
        "first_15": (
            "Isolate affected systems if safe to do so. Preserve logs and evidence. Brief operations on any "
            "manual or safe-state procedures for plant or critical equipment."
        ),
        "during": (
            "Lead technical investigation and recovery. Provide plain-language status to the crisis lead. "
            "Coordinate external IR support if engaged."
        ),
        "decisions": ["System isolation and recovery prioritisation"],
        "coordinates": ["Operations for OT impact", "Legal for breach notification", "Communications if data exposed"],
        "stand_down": "Hand back to IT operations with documented recovery and monitoring plan.",
    },
}

SCENARIO_ROLE_TASKS: dict[str, dict[str, str]] = {
    "operations": {
        "crisis": "Set objectives for operational stabilisation, prioritise resources, and chair coordination.",
        "operations": "Lead site safety, assess production impact, and sequence recovery.",
        "communications": "Prepare factual internal updates for affected sites and shift workers.",
        "legal": "Assess regulatory notification obligations and evidence preservation needs.",
        "hr": "Track personnel welfare; activate family liaison if injuries or missing persons occur.",
        "it": "Support only if control systems or business systems are involved.",
    },
    "cyber": {
        "crisis": "Activate full CMT if safety, production, or sensitive data are affected at scale.",
        "operations": "Implement safe-state or manual operations while systems are contained.",
        "communications": "Prepare breach or service-disruption messaging if external parties are affected.",
        "legal": "Lead breach-notification analysis and insurer engagement.",
        "hr": "Support employees if personal data or payroll systems are impacted.",
        "it": "Lead containment, eradication, and recovery.",
    },
    "reputation": {
        "crisis": "Own narrative and stakeholder strategy; align all spokespeople.",
        "operations": "Provide verified facts and an operational timeline — no speculation.",
        "communications": "Lead media, customer, and donor communications.",
        "legal": "Clear statements and assess defamation or contractual exposure.",
        "hr": "Brief managers on employee talking points.",
        "it": "Monitor for information leaks or social engineering.",
    },
    "people": {
        "crisis": "Make people-first priorities explicit in crisis objectives.",
        "operations": "Secure the scene and preserve access for responders.",
        "communications": "Coordinate careful internal messaging; no names until families are informed.",
        "legal": "Advise on reporting duties and privilege.",
        "hr": "Lead welfare, family liaison, and casualty tracking.",
        "it": "Support welfare checks if communication systems are strained.",
    },
    "supply": {
        "crisis": "Set objectives for customer continuity, supplier alternatives, and executive visibility.",
        "operations": "Quantify production impact, activate alternate sourcing, and report every 30 minutes.",
        "communications": "Prepare customer and supplier holding messages with approved facts only.",
        "legal": "Review contractual SLA exposure and force-majeure considerations.",
        "hr": "Brief workforce on shift changes or temporary layoffs if production stops.",
        "it": "Support if ERP, planning, or logistics systems constrain recovery options.",
    },
    "default": {
        "crisis": "Convene activated roles, declare objectives, and assign a scribe.",
        "operations": "Stabilise affected operations and report status every 30 minutes until directed otherwise.",
        "communications": "Issue an internal holding statement and monitor external channels.",
        "legal": "Advise on notification and evidence preservation.",
        "hr": "Stand by for workforce welfare needs.",
        "it": "Stand by unless technology is implicated.",
    },
}

OPENING_BY_CATEGORY: dict[str, str] = {
    "operations": (
        "Secure the scene, account for all personnel, call emergency services if required, and notify the "
        "site or programme lead. Do not wait for CMT assembly before acting to protect people."
    ),
    "cyber": (
        "Report the anomaly to IT and the site lead immediately. Do not power down safety-critical OT "
        "without operations confirmation. Preserve logs and avoid wiping systems."
    ),
    "people": (
        "Ensure immediate life safety, call emergency services if required, and notify HR to prepare "
        "family liaison protocols before any wider communication."
    ),
    "reputation": (
        "Document verified facts only. Notify the communications lead and crisis lead — avoid ad hoc "
        "statements to media, customers, or social channels."
    ),
    "supply": (
        "Confirm which customer commitments are at risk and notify the site lead and crisis lead of "
        "production impact. Do not promise delivery dates until operations validates capacity."
    ),
}

ESCALATION_BY_CATEGORY: dict[str, str] = {
    "operations": (
        "Escalate if there are injuries, conditions remain uncontrolled, regulators intervene, multiple "
        "sites are affected, or the situation cannot stabilise within four hours."
    ),
    "cyber": (
        "Escalate if safety systems are affected, sensitive data exfiltration is confirmed, operations "
        "must run in manual safe-state beyond 24 hours, or regulators require notification."
    ),
    "people": (
        "Escalate if there are fatalities, missing persons, kidnapping, or family inquiries before "
        "official notification is complete."
    ),
    "reputation": (
        "Escalate if national media coverage begins, customers threaten contract termination, or "
        "incorrect information is circulating publicly."
    ),
    "supply": (
        "Escalate if customer SLA breach is imminent, alternate sourcing fails, or financial exposure "
        "exceeds pre-agreed thresholds."
    ),
}


def _role_key(role_name: str) -> str:
    lowered = role_name.lower()
    for key, profile in ROLE_PROFILES.items():
        if any(fragment in lowered for fragment in profile["match"]):  # type: ignore[index]
            return key
    return "operations"


def _match_role_in_roster(fragment: str, roster: list[str]) -> str | None:
    frag = fragment.lower()
    for name in roster:
        if frag in name.lower():
            return name
    return None


def _roles_for_risk(risk: RiskItem, roster: list[str]) -> list[str]:
    title = risk.title.lower()
    activated: list[str] = []
    for keywords, role_fragments in RISK_ROLE_HINTS:
        if any(kw in title for kw in keywords):
            for frag in role_fragments:
                match = _match_role_in_roster(frag, roster)
                if match and match not in activated:
                    activated.append(match)

    crisis_lead = _match_role_in_roster("crisis", roster)
    if crisis_lead and crisis_lead not in activated and risk.tier <= 2:
        activated.append(crisis_lead)

    ops = _match_role_in_roster("operations", roster) or _match_role_in_roster("safety", roster)
    if ops and ops not in activated:
        activated.insert(0, ops)

    if not activated and crisis_lead:
        activated.append(crisis_lead)
    return activated


def _scenario_category(risk: RiskItem) -> str:
    title = risk.title.lower()
    if any(k in title for k in ("cyber", "ot", "ics", "ransomware")):
        return "cyber"
    if any(k in title for k in ("media", "reputation", "recall", "quality")):
        return "reputation"
    if any(k in title for k in ("injur", "fatal", "casualty", "kidnap", "traveler", "field staff")):
        return "people"
    if any(k in title for k in ("supply", "supplier", "sole-source", "logistics")):
        return "supply"
    return "operations"


def _normalize_decision(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _decisions_overlap(a: str, b: str) -> bool:
    na, nb = _normalize_decision(a), _normalize_decision(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    return False


def _dedupe_decisions(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if not any(_decisions_overlap(item, existing) for existing in result):
            result.append(item)
    return result


def _crisis_level_for_tier(tier: int, governance: GovernanceOutput) -> tuple[int, str]:
    level_map = {1: 3, 2: 2, 3: 1}
    level_num = level_map.get(tier, 2)
    for level in governance.crisis_levels:
        if level.level == level_num:
            return level_num, level.name
    return level_num, f"Level {level_num}"


def build_playbook_roles(governance: GovernanceOutput) -> list[PlaybookRole]:
    roles: list[PlaybookRole] = []
    for cmt_role in governance.crisis_team_roles:
        key = _role_key(cmt_role.role)
        profile = ROLE_PROFILES.get(key, ROLE_PROFILES["operations"])
        decisions = _dedupe_decisions(list(profile["decisions"]))  # type: ignore[arg-type]
        if cmt_role.primary_authority:
            decisions = _dedupe_decisions(decisions + list(cmt_role.primary_authority))

        roles.append(
            PlaybookRole(
                role=cmt_role.role,
                alternate_role=cmt_role.alternate_role,
                activates_when=str(profile["activates_when"]),
                purpose=str(profile["purpose"]),
                first_15_minutes=str(profile["first_15"]),
                during_response=str(profile["during"]),
                decisions=decisions,
                coordinates_with=list(profile["coordinates"]),  # type: ignore[arg-type]
                stand_down=str(profile["stand_down"]),
            )
        )
    return roles


def build_role_playbook(governance: GovernanceOutput, engagement_id: str | None = None) -> PlaybookBundle:
    return PlaybookBundle(
        roles=build_playbook_roles(governance),
        engagement_id=engagement_id,
    )


def _task_for_role(category: str, role_name: str) -> str:
    key = _role_key(role_name)
    templates = SCENARIO_ROLE_TASKS.get(category, SCENARIO_ROLE_TASKS["default"])
    return templates.get(key, templates.get("operations", ""))


def build_scenario_procedure(
    risk: RiskItem,
    governance: GovernanceOutput,
    roster: list[str],
) -> ProcedureOutput:
    level_num, level_name = _crisis_level_for_tier(risk.tier, governance)
    activated = _roles_for_risk(risk, roster)
    category = _scenario_category(risk)

    role_actions = [RoleAction(role=role, summary=_task_for_role(category, role)) for role in activated]

    opening = OPENING_BY_CATEGORY.get(category, OPENING_BY_CATEGORY["operations"])

    activation = (
        f"Declare **Level {level_num} ({level_name})** when this scenario is confirmed. "
        f"The following roles are activated: {', '.join(activated)}. "
        "The crisis lead confirms the level and chairs coordination."
    )

    escalation = ESCALATION_BY_CATEGORY.get(
        category,
        "Escalate to the next crisis level if impact spreads, regulators intervene, or the situation "
        "cannot stabilise within four hours.",
    )

    recovery_by_category = {
        "supply": (
            "After stand-down, document supplier alternatives tested, update the risk register, and brief "
            "procurement and customer account teams on residual exposure."
        ),
        "cyber": (
            "After stand-down, complete a hot wash within 48 hours, preserve forensic evidence, update "
            "the risk register, and assign owners for hardening actions."
        ),
    }
    recovery = recovery_by_category.get(
        category,
        "After stand-down, complete a hot wash within 48 hours, update the risk register, and assign "
        "owners for corrective actions. Support affected employees and families as needed.",
    )

    from cmp.models.schemas import ProcedureSection

    return ProcedureOutput(
        risk_id=risk.id,
        title=risk.title,
        procedure=ProcedureSection(
            purpose=f"Activate the right roles when the organization faces: {risk.title}.",
            scope="All affected sites, activated crisis roles, and designated site or programme leads.",
            activation_summary=activation,
            crisis_level=level_num,
            crisis_level_name=level_name,
            opening_steps=opening,
            activated_roles=activated,
            role_actions=role_actions,
            escalation_summary=escalation,
            recovery_summary=recovery,
        ),
    )


def roster_from_governance(governance: GovernanceOutput) -> list[str]:
    return [role.role for role in governance.crisis_team_roles]


def role_slug(role_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", role_name.lower()).strip("-")
