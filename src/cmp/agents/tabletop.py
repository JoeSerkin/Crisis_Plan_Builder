"""Tabletop Exercise Agent — scenario and injects from risk profile."""

from __future__ import annotations

from cmp.models.schemas import RiskProfileOutput, TabletopInject, TabletopOutput


def run_tabletop(
    risk_profile: RiskProfileOutput,
    engagement_id: str | None = None,
) -> TabletopOutput:
    primary = risk_profile.tier_1_risks[0] if risk_profile.tier_1_risks else None
    title = primary.title if primary else "Operational crisis scenario"
    scenario = (
        f"At 14:30 local time on a production day, a {title.lower()} occurs at your largest manufacturing site. "
        "Local emergency services are en route. Social media posts begin appearing within 20 minutes. "
        "A regional news outlet requests comment. The site manager has initiated evacuation of the affected area."
    )

    injects = [
        TabletopInject(
            time_offset_minutes=0,
            inject="Alarm activated in production hall. Two employees report smoke inhalation. Site manager calls emergency services.",
            expected_actions=["Account for personnel", "Notify regional leadership", "Log initial situation report"],
        ),
        TabletopInject(
            time_offset_minutes=15,
            inject="HR reports family members calling main switchboard. No family liaison protocol has been activated.",
            expected_actions=["Activate family liaison role", "Centralize family inquiries", "Prepare holding statement"],
        ),
        TabletopInject(
            time_offset_minutes=30,
            inject="Legal advises a regulatory reporting deadline may apply within 2 hours. CMT not yet formally activated.",
            expected_actions=["Crisis Director activates CMT", "Assign regulatory lead", "Confirm notification timeline"],
        ),
        TabletopInject(
            time_offset_minutes=60,
            inject="Supply chain lead warns a sole-source component line will halt within 24 hours if site remains closed.",
            expected_actions=["Assess customer impact", "Engage alternate supplier options", "Executive decision on communication"],
        ),
        TabletopInject(
            time_offset_minutes=90,
            inject="CEO asks for a single-page situation brief for board notification consideration.",
            expected_actions=["Synthesize What/So What/What Now", "Recommend board notification timing", "Document decisions"],
        ),
    ]

    return TabletopOutput(
        scenario=scenario,
        injects=injects,
        learning_objectives=[
            "Validate crisis activation criteria and CMT convening timeline",
            "Test escalation matrix and 24/7 contact effectiveness",
            "Evaluate communications coordination under media pressure",
            "Assess regulatory notification and legal coordination",
            "Identify gaps in site-to-enterprise information flow",
        ],
        evaluation_criteria=[
            "CMT activated within 30 minutes of inject 3",
            "All roles present or accounted for with alternates",
            "No unauthorized media statements",
            "Regulatory notification timeline identified",
            "Decision log maintained throughout exercise",
            "Clear stand-down and hot-wash scheduled",
        ],
        engagement_id=engagement_id,
    )
