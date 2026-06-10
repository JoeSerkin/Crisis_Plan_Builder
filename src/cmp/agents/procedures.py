"""Procedure Builder Agent — role-based scenario activation cards."""

from __future__ import annotations

from cmp.agents.governance import run_governance
from cmp.models.schemas import GovernanceOutput, ProceduresBundle, RiskProfileOutput
from cmp.render.playbook_builder import build_scenario_procedure, roster_from_governance


def run_procedures(
    risk_profile: RiskProfileOutput,
    engagement_id: str | None = None,
    governance: GovernanceOutput | None = None,
) -> ProceduresBundle:
    gov = governance or run_governance(engagement_id=engagement_id)
    roster = roster_from_governance(gov)

    procedures = [
        build_scenario_procedure(risk, gov, roster)
        for risk in risk_profile.tier_1_risks + risk_profile.tier_2_risks
    ]
    return ProceduresBundle(procedures=procedures, engagement_id=engagement_id)
