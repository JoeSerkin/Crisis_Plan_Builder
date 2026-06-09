"""Procedure Builder Agent — response procedures per identified risk."""

from __future__ import annotations

from cmp.models.schemas import ProcedureOutput, ProcedureSection, ProceduresBundle, RiskProfileOutput


def _procedure_for_risk(risk_id: str, title: str) -> ProcedureSection:
    return ProcedureSection(
        purpose=f"Provide structured response actions for: {title}",
        scope="All affected sites, CMT members, and designated site crisis leads.",
        activation_criteria=[
            f"Event matches risk scenario: {title}",
            "Site Manager or Crisis Director confirms activation threshold",
            "Potential impact exceeds Level 2 severity indicators",
        ],
        immediate_actions=[
            "Ensure personnel safety and account for all staff in affected area",
            "Notify Site Manager and activate site crisis lead",
            "Establish crisis bridge / communication channel",
            "Begin situation report using What / So What / What Now format",
            "Preserve evidence and logs; restrict non-essential access to affected area",
        ],
        ongoing_actions=[
            "CMT convenes within defined escalation timeframe",
            "Maintain situational log with decision record",
            "Coordinate with legal, communications, and regulators as required",
            "Issue periodic internal updates to leadership and affected employees",
            "Track resource needs, casualties, and operational impacts",
        ],
        escalation_triggers=[
            "Fatalities or serious injuries",
            "Media or social media attention",
            "Regulatory agency involvement",
            "Impact spreads to additional sites or countries",
            "Inability to contain within 4 hours",
        ],
        recovery_considerations=[
            "Conduct hot wash within 48 hours of stand-down",
            "Document lessons learned and update risk register",
            "Assess need for employee support and family liaison",
            "Validate business continuity and alternate site readiness",
            "Schedule tabletop exercise if gaps identified",
        ],
    )


def run_procedures(
    risk_profile: RiskProfileOutput,
    engagement_id: str | None = None,
) -> ProceduresBundle:
    procedures: list[ProcedureOutput] = []
    for risk in risk_profile.tier_1_risks + risk_profile.tier_2_risks:
        procedures.append(
            ProcedureOutput(
                risk_id=risk.id,
                title=risk.title,
                procedure=_procedure_for_risk(risk.id, risk.title),
                engagement_id=engagement_id,
            )
        )
    return ProceduresBundle(procedures=procedures, engagement_id=engagement_id)
