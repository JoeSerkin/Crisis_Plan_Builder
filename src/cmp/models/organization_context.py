"""Resolve organization size, maturity, and jurisdiction context from intake."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cmp.models.requirements import GapPriority, Requirement, knowledge_root, load_yaml
from cmp.models.schemas import ClientIntake, OrganizationContextSummary


@dataclass
class OrganizationContext:
    size_tier: str
    employee_count: int | None
    country_count: int
    site_count: int
    headquarters_country: str | None
    crisis_maturity: str | None
    staffing_model: str | None
    min_cmt_roles: int = 5
    min_procedures: int = 3
    readiness_gate: int = 60
    flexibility_notes: list[str] = field(default_factory=list)
    jurisdiction_notes: list[str] = field(default_factory=list)
    priority_downgrades: dict[str, str] = field(default_factory=dict)
    priority_boosts: dict[str, str] = field(default_factory=dict)


def _count_sites(intake: ClientIntake) -> int:
    if intake.sites:
        return len(intake.sites)
    sites = intake.additional_context.get("sites")
    if isinstance(sites, list):
        return len(sites)
    return 0


def _resolve_size_tier(intake: ClientIntake, tiers: dict[str, Any]) -> str:
    explicit = (intake.organization_size or intake.additional_context.get("organization_size") or "").strip().lower()
    if explicit in tiers:
        return explicit

    employees = intake.employees
    if employees is None:
        return "medium"

    for tier_name in ("small", "medium", "large"):
        tier = tiers.get(tier_name, {})
        max_employees = tier.get("max_employees")
        if max_employees is not None and employees <= int(max_employees):
            return tier_name
    return "enterprise"


def resolve_organization_context(intake: ClientIntake, root: Path | None = None) -> OrganizationContext:
    root = root or knowledge_root()
    raw = load_yaml(root / "crisis_management" / "organization_context.yaml")
    tiers = raw.get("size_tiers", {})

    size_tier = _resolve_size_tier(intake, tiers)
    tier_cfg = tiers.get(size_tier, {})

    headquarters = intake.headquarters_country or intake.additional_context.get("headquarters_country")
    if isinstance(headquarters, str):
        headquarters = headquarters.strip() or None

    maturity = intake.crisis_program_maturity or intake.additional_context.get("crisis_program_maturity")
    if isinstance(maturity, str):
        maturity = maturity.strip().lower() or None

    staffing = intake.staffing_model or intake.additional_context.get("staffing_model")
    if isinstance(staffing, str):
        staffing = staffing.strip().lower() or None

    site_count = _count_sites(intake)
    country_count = len(intake.countries)

    flexibility_notes: list[str] = list(tier_cfg.get("context_notes", []))

    maturity_cfg = raw.get("maturity_guidance", {}).get(maturity or "", {})
    flexibility_notes.extend(maturity_cfg.get("context_notes", []))

    staffing_cfg = raw.get("staffing_guidance", {}).get(staffing or "", {})
    flexibility_notes.extend(staffing_cfg.get("context_notes", []))

    if site_count <= 1 and country_count <= 1:
        flexibility_notes.append(
            "Single-site, single-country organizations may use simplified site crisis lead and escalation models."
        )

    jurisdiction_notes: list[str] = []
    priority_boosts: dict[str, str] = {}
    countries_lower = {country.strip().lower() for country in intake.countries if country.strip()}
    if headquarters:
        countries_lower.add(headquarters.lower())

    for profile in raw.get("jurisdiction_profiles", []):
        matches = {country.strip().lower() for country in profile.get("match_countries", [])}
        if countries_lower.intersection(matches):
            jurisdiction_notes.extend(profile.get("context_notes", []))
            for req_id, priority in profile.get("priority_boost", {}).items():
                priority_boosts[req_id] = priority

    downgrades = dict(tier_cfg.get("priority_downgrade", {}))
    if site_count > 1 or country_count > 1:
        downgrades.pop("GOV-012", None)

    readiness_gate = 60 + int(maturity_cfg.get("readiness_gate_adjustment", 0))

    return OrganizationContext(
        size_tier=size_tier,
        employee_count=intake.employees,
        country_count=country_count,
        site_count=site_count,
        headquarters_country=headquarters,
        crisis_maturity=maturity,
        staffing_model=staffing,
        min_cmt_roles=int(tier_cfg.get("min_cmt_roles", 5)),
        min_procedures=int(tier_cfg.get("min_procedures", 3)),
        readiness_gate=readiness_gate,
        flexibility_notes=_dedupe(flexibility_notes),
        jurisdiction_notes=_dedupe(jurisdiction_notes),
        priority_downgrades=downgrades,
        priority_boosts=priority_boosts,
    )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def apply_organization_context(
    requirements: list[Requirement],
    context: OrganizationContext,
) -> list[Requirement]:
    for req in requirements:
        if req.id in context.priority_downgrades:
            new_priority = GapPriority(context.priority_downgrades[req.id])
            if _priority_rank(new_priority) > _priority_rank(req.priority):
                req.priority = new_priority
        if req.id in context.priority_boosts:
            boosted = GapPriority(context.priority_boosts[req.id])
            if _priority_rank(boosted) < _priority_rank(req.priority):
                req.priority = boosted
    return requirements


def _priority_rank(priority: GapPriority) -> int:
    order = {
        GapPriority.CRITICAL: 0,
        GapPriority.HIGH: 1,
        GapPriority.MEDIUM: 2,
        GapPriority.LOW: 3,
    }
    return order[priority]


def to_summary(context: OrganizationContext) -> OrganizationContextSummary:
    return OrganizationContextSummary(
        size_tier=context.size_tier,
        employee_count=context.employee_count,
        country_count=context.country_count,
        site_count=context.site_count,
        headquarters_country=context.headquarters_country,
        crisis_maturity=context.crisis_maturity,
        staffing_model=context.staffing_model,
        min_cmt_roles=context.min_cmt_roles,
        min_procedures=context.min_procedures,
        readiness_gate=context.readiness_gate,
        flexibility_notes=context.flexibility_notes,
        jurisdiction_notes=context.jurisdiction_notes,
    )
