"""Build requirement gap lists used as document extraction targets."""

from __future__ import annotations

from cmp.models.requirements import (
    filter_requirements_for_industry,
    load_industry_modifier,
    load_requirements_catalog,
)
from cmp.models.schemas import RequirementGap
from cmp.storage.engagement_store import EngagementStore


def catalog_gaps_for_extraction(
    store: EngagementStore,
    engagement_id: str,
) -> list[RequirementGap]:
    """All catalog fields for the engagement industry — used as extraction targets."""
    intake = store.load_intake(engagement_id)
    catalog = load_requirements_catalog()
    modifier = load_industry_modifier(intake.industry) if intake and intake.industry else None
    requirements = filter_requirements_for_industry(catalog, modifier)
    record = store.get_engagement(engagement_id)
    resolved = set(record.resolved_requirement_ids if record else [])
    seen: set[str] = set()
    gaps: list[RequirementGap] = []
    for req in requirements:
        if req.id in resolved or req.field_path in seen:
            continue
        seen.add(req.field_path)
        gaps.append(
            RequirementGap(
                requirement_id=req.id,
                domain=req.domain,
                label=req.label,
                priority=req.priority,
                why_it_matters=req.why_it_matters,
                unlocks_agents=req.unlocks_agents,
                field_path=req.field_path,
            )
        )
    return gaps
