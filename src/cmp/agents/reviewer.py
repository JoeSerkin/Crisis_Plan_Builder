"""Standards Review Agent — framework coverage assessment."""

from __future__ import annotations

from cmp.models.schemas import (
    ChecklistVerification,
    DiscoveryOutput,
    GovernanceOutput,
    KnownField,
    ProceduresBundle,
    StandardsReviewOutput,
)


def _field_present(discovery: DiscoveryOutput, field_path: str) -> bool:
    known = discovery.known_information.get(field_path)
    if known is None:
        return False
    if isinstance(known, KnownField):
        value = known.value
    else:
        value = known.get("value")
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _run_checklist_verifications(
    discovery: DiscoveryOutput,
    governance: GovernanceOutput | None,
    procedures: ProceduresBundle | None,
) -> list[ChecklistVerification]:
    proc_count = len(procedures.procedures) if procedures else 0
    role_count = len(governance.crisis_team_roles) if governance else 0
    org = discovery.organization_context
    min_roles = org.min_cmt_roles if org else 5
    min_procedures = org.min_procedures if org else 3
    readiness_gate = org.readiness_gate if org else 60

    checks: list[tuple[str, bool, str]] = [
        (
            "Crisis management policy and scope documented",
            governance is not None and len(governance.crisis_levels) >= 4 and proc_count >= 1,
            "Requires crisis levels and at least one response procedure.",
        ),
        (
            "Crisis management objectives aligned to organizational context",
            discovery.planning_readiness_score >= readiness_gate,
            f"Requires planning readiness score at or above the risk profiling gate ({readiness_gate}).",
        ),
        (
            "Crisis management team structure and roles defined",
            role_count >= min_roles,
            f"Requires at least {min_roles} CMT roles for this organization size and staffing model.",
        ),
        (
            "Competence and training requirements for CMT members",
            _field_present(discovery, "crisis_comms_training")
            or _field_present(discovery, "last_tabletop_exercise"),
            "Requires crisis communications training or recent exercise history in intake.",
        ),
        (
            "Crisis communication procedures (internal and external)",
            _field_present(discovery, "spokesperson_policy")
            and _field_present(discovery, "internal_comms_channels"),
            "Requires spokesperson policy and internal crisis channels in intake.",
        ),
        (
            "Warning and notification systems established",
            _field_present(discovery, "after_hours_escalation")
            and _field_present(discovery, "internal_comms_channels"),
            "Requires 24/7 escalation contacts and internal notification channels.",
        ),
        (
            "Monitoring and detection of potential crises",
            _field_present(discovery, "social_media_monitoring")
            or _field_present(discovery, "monitoring_alert_services"),
            "Requires social media monitoring or dedicated alert services in intake.",
        ),
        (
            "Crisis assessment and decision-making process",
            _field_present(discovery, "crisis_activation_criteria")
            and _field_present(discovery, "decision_authorities"),
            "Requires activation criteria and decision authorities in intake.",
        ),
        (
            "Crisis response procedures for identified scenarios",
            proc_count >= min_procedures,
            f"Requires response procedures for at least {min_procedures} identified risks.",
        ),
        (
            "Exercise and testing program (tabletop, simulation)",
            _field_present(discovery, "last_tabletop_exercise")
            or _field_present(discovery, "tabletop_history"),
            "Requires recent tabletop exercise or documented exercise history.",
        ),
        (
            "Review and continual improvement after incidents and exercises",
            _field_present(discovery, "post_incident_review"),
            "Requires a documented post-incident review process in intake.",
        ),
        (
            "Documented interfaces with business continuity and emergency response",
            _field_present(discovery, "existing_bcp")
            and _field_present(discovery, "existing_crisis_plan"),
            "Requires both BCP and crisis plan references in intake.",
        ),
    ]

    return [
        ChecklistVerification(
            item=item,
            status="pass" if passed else "fail",
            note="" if passed else note,
        )
        for item, passed, note in checks
    ]


def run_standards_review(
    discovery: DiscoveryOutput,
    governance: GovernanceOutput | None = None,
    procedures: ProceduresBundle | None = None,
    engagement_id: str | None = None,
) -> StandardsReviewOutput:
    strengths: list[str] = []
    gaps: list[str] = []
    recommendations: list[str] = []

    verifications = _run_checklist_verifications(discovery, governance, procedures)
    passed_count = sum(1 for check in verifications if check.status == "pass")
    coverage_score = int(round((passed_count / len(verifications)) * 100)) if verifications else 0

    if discovery.planning_readiness_score >= (discovery.organization_context.readiness_gate if discovery.organization_context else 60):
        strengths.append("Planning readiness gate passed — sufficient intake for risk profiling.")
    min_roles = discovery.organization_context.min_cmt_roles if discovery.organization_context else 5
    if governance and len(governance.crisis_team_roles) >= min_roles:
        strengths.append("CMT role structure defined with decision authority separation.")
    min_procedures = discovery.organization_context.min_procedures if discovery.organization_context else 3
    if procedures and len(procedures.procedures) >= min_procedures:
        strengths.append("Tier 1/2 risks have documented response procedure skeletons.")

    for check in verifications:
        if check.status == "fail":
            gaps.append(f"ISO 22361 checklist: {check.item} — {check.note}")

    if discovery.critical_gaps:
        gaps.insert(
            0,
            f"{len(discovery.critical_gaps)} critical discovery gaps remain "
            f"(e.g., {', '.join(discovery.critical_gaps[:3])}).",
        )

    recommendations.extend(
        [
            "Resolve all failed checklist verifications before client delivery.",
            "Adapt CMT design to organization size — dual-hat roles are acceptable when documented with named alternates.",
            "Map insurance, regulatory, and notification obligations to each operating jurisdiction — not just headquarters.",
            "Conduct tabletop exercise within 90 days of plan approval.",
            "Label deliverable as draft for consultant review — not ISO certification.",
        ]
    )

    return StandardsReviewOutput(
        strengths=strengths,
        gaps=gaps,
        recommendations=recommendations,
        framework_coverage_score=coverage_score,
        checklist_verifications=verifications,
        engagement_id=engagement_id,
    )
