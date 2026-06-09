"""Governance Design Agent — crisis structure and escalation."""

from __future__ import annotations

from cmp.models.schemas import (
    CrisisLevel,
    CrisisTeamRole,
    DecisionAuthority,
    DiscoveryOutput,
    EscalationStep,
    GovernanceOutput,
)


def _default_cmt_roles() -> list[CrisisTeamRole]:
    return [
        CrisisTeamRole(
            role="Crisis Director",
            responsibilities=["Activate CMT", "Set objectives", "Authorize major decisions", "Declare stand-down"],
            primary_authority=["Crisis activation", "Resource allocation", "External spokesperson approval"],
            alternate_role="Deputy Crisis Director",
        ),
        CrisisTeamRole(
            role="Operations Lead",
            responsibilities=["Site status", "Production impacts", "Recovery sequencing"],
            primary_authority=["Operational shutdown/restart recommendations"],
        ),
        CrisisTeamRole(
            role="Communications Lead",
            responsibilities=["Internal/external messaging", "Media monitoring", "Spokesperson coordination"],
            primary_authority=["Approved holding statements", "Employee notifications"],
        ),
        CrisisTeamRole(
            role="Legal & Regulatory Lead",
            responsibilities=["Regulatory notification", "Privilege management", "Investigation coordination"],
            primary_authority=["Regulator contact approval"],
        ),
        CrisisTeamRole(
            role="HR / People Lead",
            responsibilities=["Employee welfare", "Family liaison", "Casualty tracking"],
            primary_authority=["Family notification protocol initiation"],
        ),
        CrisisTeamRole(
            role="IT / Cyber Lead",
            responsibilities=["Technology continuity", "Cyber incident coordination", "OT/ICS liaison"],
            primary_authority=["System isolation recommendations"],
        ),
    ]


def _lean_cmt_roles() -> list[CrisisTeamRole]:
    return [
        CrisisTeamRole(
            role="Crisis Lead",
            responsibilities=[
                "Activate response team",
                "Set objectives",
                "Authorize major decisions",
                "Serve as primary internal and external coordination point",
            ],
            primary_authority=["Crisis activation", "Resource allocation", "External spokesperson approval"],
            alternate_role="Deputy Crisis Lead",
        ),
        CrisisTeamRole(
            role="Operations & Safety Lead",
            responsibilities=[
                "Site status and life safety",
                "Production impacts",
                "Local emergency services liaison",
            ],
            primary_authority=["Evacuation and operational shutdown recommendations"],
            alternate_role="Crisis Lead",
        ),
        CrisisTeamRole(
            role="People & Communications Lead",
            responsibilities=[
                "Employee and family welfare",
                "Internal notifications",
                "Spokesperson coordination",
            ],
            primary_authority=["Employee notifications", "Approved holding statements"],
            alternate_role="Crisis Lead",
        ),
        CrisisTeamRole(
            role="Legal, Insurance & Compliance Lead",
            responsibilities=[
                "Regulatory notification",
                "Insurance and broker coordination",
                "Privilege management",
            ],
            primary_authority=["Regulator and insurer contact approval"],
            alternate_role="Crisis Lead",
        ),
    ]


def run_governance(
    discovery: DiscoveryOutput | None = None,
    engagement_id: str | None = None,
) -> GovernanceOutput:
    crisis_levels = [
        CrisisLevel(
            level=1,
            name="Incident",
            description="Localized event managed by site/department with no CMT activation.",
            activation_triggers=["No injuries", "No media interest", "Contained within 4 hours"],
        ),
        CrisisLevel(
            level=2,
            name="Serious Incident",
            description="Significant event requiring regional leadership and partial CMT stand-up.",
            activation_triggers=["Injuries requiring medical evacuation", "Regulatory interest", "Local media"],
        ),
        CrisisLevel(
            level=3,
            name="Crisis",
            description="Full CMT activation with executive decision authority.",
            activation_triggers=["Fatalities", "Major operational shutdown", "National media", "Regulatory order"],
        ),
        CrisisLevel(
            level=4,
            name="Corporate Crisis",
            description="Enterprise-wide impact requiring board notification and potential external crisis support.",
            activation_triggers=["Multi-site impact", "Material financial exposure", "CEO/Board engagement required"],
        ),
    ]

    escalation_matrix = [
        EscalationStep(severity="Level 1", notify_within_minutes=60, roles=["Site Manager"], channel="Phone/SMS"),
        EscalationStep(
            severity="Level 2",
            notify_within_minutes=30,
            roles=["Site Manager", "Regional Director", "Security/EHS Lead"],
            channel="Phone bridge",
        ),
        EscalationStep(
            severity="Level 3",
            notify_within_minutes=15,
            roles=["Crisis Director", "CMT Core", "Legal", "Communications"],
            channel="Crisis bridge + secure messaging",
        ),
        EscalationStep(
            severity="Level 4",
            notify_within_minutes=15,
            roles=["CEO", "Board Liaison", "Full CMT", "External Advisors"],
            channel="Executive bridge",
        ),
    ]

    org = discovery.organization_context if discovery else None
    if org and org.size_tier == "small":
        crisis_team_roles = _lean_cmt_roles()
    else:
        crisis_team_roles = _default_cmt_roles()

    decision_authorities = [
        DecisionAuthority(
            decision_type="Crisis activation",
            authority_role="Crisis Director",
            backup_role="CEO",
            notes="CEO may pre-delegate activation authority in writing.",
        ),
        DecisionAuthority(
            decision_type="Site evacuation",
            authority_role="Site Manager",
            backup_role="Crisis Director",
            notes="Life safety decisions may be taken immediately; inform CMT within 15 minutes.",
        ),
        DecisionAuthority(
            decision_type="Production shutdown",
            authority_role="Operations Lead",
            backup_role="Crisis Director",
        ),
        DecisionAuthority(
            decision_type="Media statement",
            authority_role="Communications Lead",
            backup_role="CEO",
            notes="All statements require Crisis Director or CEO approval for Level 3+.",
        ),
        DecisionAuthority(
            decision_type="Regulatory notification",
            authority_role="Legal & Regulatory Lead",
            backup_role="Crisis Director",
        ),
    ]

    if discovery and discovery.critical_gaps:
        for role in crisis_team_roles:
            role.responsibilities.append(
                "[CONSULTANT NOTE] Populate named individuals — discovery gaps remain for CMT membership."
            )
            break
    elif org and org.flexibility_notes:
        crisis_team_roles[0].responsibilities.append(f"[ORG CONTEXT] {org.flexibility_notes[0]}")

    return GovernanceOutput(
        crisis_levels=crisis_levels,
        escalation_matrix=escalation_matrix,
        crisis_team_roles=crisis_team_roles,
        decision_authorities=decision_authorities,
        engagement_id=engagement_id,
    )
