"""Risk Profiling Agent — tiered organizational risk profile."""

from __future__ import annotations

from cmp.models.schemas import ClientIntake, DiscoveryOutput, RiskItem, RiskProfileOutput


def _base_manufacturing_risks(countries: list[str]) -> tuple[list[RiskItem], list[RiskItem], list[RiskItem]]:
    tier_1 = [
        RiskItem(
            id="R-T1-001",
            title="Industrial accident (fire, explosion, chemical release)",
            tier=1,
            rationale="Manufacturing operations involve hazardous processes and high-consequence physical incidents.",
            likelihood="medium",
            impact="critical",
            affected_domains=["operations_sites", "governance"],
        ),
        RiskItem(
            id="R-T1-002",
            title="Supply chain disruption — sole-source supplier failure",
            tier=1,
            rationale="Production continuity depends on critical suppliers; disruption halts output and affects customers.",
            likelihood="medium",
            impact="high",
            affected_domains=["operations_sites", "risk_bcp"],
        ),
        RiskItem(
            id="R-T1-003",
            title="Cyber incident affecting OT/ICS or ERP",
            tier=1,
            rationale="Cyber-physical incidents can force production shutdown and regulatory notification.",
            likelihood="medium",
            impact="high",
            affected_domains=["risk_bcp", "governance"],
        ),
    ]
    if len(countries) > 1:
        tier_1.append(
            RiskItem(
                id="R-T1-004",
                title="Cross-border operational crisis requiring multi-site coordination",
                tier=1,
                rationale=f"Operations span {len(countries)} countries; local incidents may require global CMT activation.",
                likelihood="medium",
                impact="high",
                affected_domains=["governance", "communications"],
            )
        )

    tier_2 = [
        RiskItem(
            id="R-T2-001",
            title="Natural hazard event affecting production site",
            tier=2,
            rationale="Sites in multiple geographies face flood, seismic, or storm exposure.",
            likelihood="medium",
            impact="high",
        ),
        RiskItem(
            id="R-T2-002",
            title="Labor dispute or industrial action",
            tier=2,
            rationale="Manufacturing workforce disruptions can halt shifts and attract media attention.",
            likelihood="low",
            impact="medium",
        ),
        RiskItem(
            id="R-T2-003",
            title="Environmental spill and regulatory enforcement",
            tier=2,
            rationale="Environmental liability requires regulator notification and community communication.",
            likelihood="low",
            impact="high",
        ),
    ]
    tier_3 = [
        RiskItem(
            id="R-T3-001",
            title="Reputational crisis from product quality defect",
            tier=3,
            rationale="Product recalls may emerge from operational incidents or supply chain failures.",
            likelihood="low",
            impact="medium",
        ),
        RiskItem(
            id="R-T3-002",
            title="Executive unavailability during concurrent incidents",
            tier=3,
            rationale="Succession gaps slow decision-making when multiple sites are affected.",
            likelihood="low",
            impact="medium",
        ),
    ]
    return tier_1, tier_2, tier_3


def _base_energy_risks(countries: list[str]) -> tuple[list[RiskItem], list[RiskItem], list[RiskItem]]:
    tier_1 = [
        RiskItem(
            id="R-T1-E01",
            title="Major accident hazard (fire, explosion, toxic release)",
            tier=1,
            rationale="High-hazard energy processes carry catastrophic consequence potential requiring MAH response.",
            likelihood="low",
            impact="critical",
            affected_domains=["operations_sites", "governance"],
        ),
        RiskItem(
            id="R-T1-E02",
            title="Pipeline or transmission infrastructure failure",
            tier=1,
            rationale="Infrastructure failures can affect wide geographic areas and require regulator notification.",
            likelihood="low",
            impact="critical",
            affected_domains=["operations_sites", "risk_bcp"],
        ),
        RiskItem(
            id="R-T1-E03",
            title="Environmental release with community impact",
            tier=1,
            rationale="Spills and releases trigger multi-agency response and sustained community engagement.",
            likelihood="medium",
            impact="high",
            affected_domains=["operations_sites", "communications"],
        ),
    ]
    tier_2 = [
        RiskItem(
            id="R-T2-E01",
            title="Process safety management system failure",
            tier=2,
            rationale="PSM gaps increase likelihood of escalating operational incidents.",
            likelihood="medium",
            impact="high",
        ),
        RiskItem(
            id="R-T2-E02",
            title="Cyber incident affecting SCADA or control systems",
            tier=2,
            rationale="Control system compromise can force emergency shutdown of critical infrastructure.",
            likelihood="medium",
            impact="high",
        ),
    ]
    tier_3 = [
        RiskItem(
            id="R-T3-E01",
            title="Regulatory enforcement action following incident",
            tier=3,
            rationale="Post-incident investigations may result in operational restrictions or penalties.",
            likelihood="medium",
            impact="medium",
        ),
    ]
    if len(countries) > 1:
        tier_2.append(
            RiskItem(
                id="R-T2-E03",
                title="Cross-jurisdictional regulatory notification complexity",
                tier=2,
                rationale=f"Operations in {len(countries)} countries require coordinated multi-regulator response.",
                likelihood="medium",
                impact="medium",
            )
        )
    return tier_1, tier_2, tier_3


def _base_pharma_risks(countries: list[str]) -> tuple[list[RiskItem], list[RiskItem], list[RiskItem]]:
    tier_1 = [
        RiskItem(
            id="R-T1-P01",
            title="Product quality crisis requiring recall",
            tier=1,
            rationale="Product defects trigger regulatory notification, recall logistics, and reputational damage.",
            likelihood="low",
            impact="critical",
            affected_domains=["risk_bcp", "governance", "communications"],
        ),
        RiskItem(
            id="R-T1-P02",
            title="GxP compliance breach during production disruption",
            tier=1,
            rationale="Quality system failures during crises may invalidate batch release and market authorization.",
            likelihood="low",
            impact="critical",
            affected_domains=["operations_sites", "governance"],
        ),
        RiskItem(
            id="R-T1-P03",
            title="Cold chain failure destroying inventory",
            tier=1,
            rationale="Temperature excursions destroy temperature-sensitive products and trigger supply shortages.",
            likelihood="medium",
            impact="high",
            affected_domains=["operations_sites", "risk_bcp"],
        ),
    ]
    tier_2 = [
        RiskItem(
            id="R-T2-P01",
            title="Adverse event requiring pharmacovigilance reporting",
            tier=2,
            rationale="Patient safety events discovered during crises require health authority notification.",
            likelihood="medium",
            impact="high",
        ),
        RiskItem(
            id="R-T2-P02",
            title="Clinical trial disruption at investigational sites",
            tier=2,
            rationale="Trial continuity affects patient safety and regulatory commitments.",
            likelihood="low",
            impact="high",
        ),
    ]
    tier_3 = [
        RiskItem(
            id="R-T3-P01",
            title="Counterfeit or supply chain integrity incident",
            tier=3,
            rationale="Supply chain integrity failures erode patient and regulator trust.",
            likelihood="low",
            impact="medium",
        ),
    ]
    return tier_1, tier_2, tier_3


def _base_ngo_risks(countries: list[str]) -> tuple[list[RiskItem], list[RiskItem], list[RiskItem]]:
    tier_1 = [
        RiskItem(
            id="R-T1-N01",
            title="Field team security incident (attack, ambush, detention)",
            tier=1,
            rationale="Field teams in program areas face targeted violence requiring immediate extraction or shelter.",
            likelihood="medium",
            impact="critical",
            affected_domains=["governance", "risk_bcp"],
        ),
        RiskItem(
            id="R-T1-N02",
            title="Kidnap or hostage situation involving staff",
            tier=1,
            rationale="K&R incidents require specialized response protocols and insurer coordination.",
            likelihood="low",
            impact="critical",
            affected_domains=["governance", "communications"],
        ),
        RiskItem(
            id="R-T1-N03",
            title="Duty-of-care failure for travelers or field staff",
            tier=1,
            rationale="NGOs bear heightened duty-of-care obligations for staff in high-risk environments.",
            likelihood="medium",
            impact="high",
            affected_domains=["governance", "procedures"],
        ),
    ]
    tier_2 = [
        RiskItem(
            id="R-T2-N01",
            title="Local partner misconduct or security breach",
            tier=2,
            rationale="Implementing partner failures create concurrent operational and reputational crises.",
            likelihood="medium",
            impact="high",
        ),
        RiskItem(
            id="R-T2-N02",
            title="Program suspension in active conflict zone",
            tier=2,
            rationale="Conflict escalation may require emergency evacuation of staff and program assets.",
            likelihood="medium",
            impact="high",
        ),
    ]
    tier_3 = [
        RiskItem(
            id="R-T3-N01",
            title="Donor confidence crisis affecting funding",
            tier=3,
            rationale="Security or integrity incidents may trigger donor withdrawal and media scrutiny.",
            likelihood="medium",
            impact="medium",
        ),
    ]
    if len(countries) > 3:
        tier_2.append(
            RiskItem(
                id="R-T2-N03",
                title="Multi-country program coordination failure",
                tier=2,
                rationale=f"Programs span {len(countries)} countries requiring coordinated crisis command.",
                likelihood="medium",
                impact="medium",
            )
        )
    return tier_1, tier_2, tier_3


def _resolve_industry_risks(
    industry: str, countries: list[str]
) -> tuple[list[RiskItem], list[RiskItem], list[RiskItem]]:
    if "manufactur" in industry:
        return _base_manufacturing_risks(countries)
    if any(k in industry for k in ("energy", "oil", "gas", "utilit", "power", "upstream", "downstream")):
        return _base_energy_risks(countries)
    if any(k in industry for k in ("pharma", "biotech", "life science", "medical device")):
        return _base_pharma_risks(countries)
    if any(k in industry for k in ("ngo", "nonprofit", "non-profit", "humanitarian", "charity", "aid")):
        return _base_ngo_risks(countries)
    t1 = [
        RiskItem(
            id="R-T1-GEN",
            title="Major operational disruption",
            tier=1,
            rationale="Generic Tier 1 operational crisis pending industry-specific profiling.",
            likelihood="medium",
            impact="high",
        )
    ]
    return t1, [], []


def run_risk_profile(
    intake: ClientIntake,
    discovery: DiscoveryOutput | None = None,
    engagement_id: str | None = None,
) -> RiskProfileOutput:
    industry = intake.industry.lower()
    t1, t2, t3 = _resolve_industry_risks(industry, intake.countries)

    rationale = {
        "methodology": "Risk tiers assigned based on industry modifier, geographic footprint, and discovery gaps.",
        "tier_1_definition": "Immediate threat to life, critical operations, or regulatory standing within 24 hours.",
        "tier_2_definition": "Significant disruption manageable within 72 hours with CMT activation.",
        "tier_3_definition": "Emerging or lower-likelihood risks requiring monitoring and procedure preparation.",
    }
    if discovery and discovery.critical_gaps:
        rationale["discovery_note"] = (
            f"Risk profile generated with {len(discovery.critical_gaps)} unresolved critical discovery gaps; "
            "validate assumptions with client before finalizing."
        )

    return RiskProfileOutput(
        tier_1_risks=t1,
        tier_2_risks=t2,
        tier_3_risks=t3,
        risk_rationale=rationale,
        engagement_id=engagement_id,
    )
