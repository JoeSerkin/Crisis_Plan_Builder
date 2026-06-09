"""Client Discovery Agent — deterministic gap analysis and readiness scoring."""

from __future__ import annotations

import os
from typing import Any

from cmp.models.requirements import (
    Requirement,
    apply_industry_modifier,
    filter_requirements_for_industry,
    load_industry_modifier,
    load_readiness_weights,
    load_requirements_catalog,
)
from cmp.models.schemas import (
    ClientIntake,
    ConsultantQuestion,
    DiscoveryOutput,
    FieldConfidence,
    GapPriority,
    KnownField,
    RequirementGap,
)


def map_known_information(intake: ClientIntake) -> dict[str, KnownField]:
    """Map intake fields to known_information — no fabrication."""
    flat = intake.flatten()
    known: dict[str, KnownField] = {}
    for field_path, value in flat.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and len(value) == 0:
            continue
        known[field_path] = KnownField(
            value=value,
            source="intake",
            confidence=FieldConfidence.STATED_BY_CLIENT,
        )
    return known


def detect_gaps(
    intake: ClientIntake,
    requirements: list[Requirement],
    resolved_ids: set[str] | None = None,
) -> list[RequirementGap]:
    resolved_ids = resolved_ids or set()
    gaps: list[RequirementGap] = []
    for req in requirements:
        if req.id in resolved_ids:
            continue
        if intake.is_field_present(req.field_path):
            continue
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


def build_questions(
    gaps: list[RequirementGap],
    requirements_by_id: dict[str, Requirement],
    use_llm: bool = False,
) -> list[ConsultantQuestion]:
    questions: list[ConsultantQuestion] = []
    priority_order = {
        GapPriority.CRITICAL: 0,
        GapPriority.HIGH: 1,
        GapPriority.MEDIUM: 2,
        GapPriority.LOW: 3,
    }
    sorted_gaps = sorted(gaps, key=lambda g: priority_order.get(g.priority, 99))
    for i, gap in enumerate(sorted_gaps):
        req = requirements_by_id.get(gap.requirement_id)
        template = req.question_template if req else f"Please provide information about {gap.label}."
        question_text = template
        if use_llm:
            question_text = _maybe_rephrase_question(template, gap, os.environ.get("GEMINI_API_KEY"))
        questions.append(
            ConsultantQuestion(
                id=f"Q-{gap.requirement_id}",
                targets_gap=gap.requirement_id,
                question=question_text,
                rationale=gap.why_it_matters,
                priority=gap.priority,
            )
        )
    return questions


def _maybe_rephrase_question(template: str, gap: RequirementGap, api_key: str | None) -> str:
    if not api_key:
        return template
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = (
            "Rephrase this consultant discovery question professionally. "
            "Do not add facts or assumptions about the client. "
            "Return only the question sentence.\n\n"
            f"Topic: {gap.label}\n"
            f"Template: {template}"
        )
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        return text if text else template
    except Exception:
        return template


def compute_readiness_breakdown(
    requirements: list[Requirement],
    known: dict[str, KnownField],
    gaps: list[RequirementGap],
    weights: dict[str, dict[str, Any]],
) -> dict[str, int]:
    breakdown: dict[str, int] = {}
    gap_ids_by_domain: dict[str, set[str]] = {}
    for gap in gaps:
        gap_ids_by_domain.setdefault(gap.domain, set()).add(gap.requirement_id)

    reqs_by_domain: dict[str, list[Requirement]] = {}
    for req in requirements:
        reqs_by_domain.setdefault(req.domain, []).append(req)

    for domain, domain_reqs in reqs_by_domain.items():
        total = len(domain_reqs)
        if total == 0:
            breakdown[domain] = 0
            continue
        satisfied = sum(1 for r in domain_reqs if r.field_path in known)
        domain_gaps = gap_ids_by_domain.get(domain, set())
        critical_penalty = sum(
            1 for r in domain_reqs if r.id in domain_gaps and r.priority == GapPriority.CRITICAL
        )
        base_score = int(round((satisfied / total) * 100))
        penalty = min(30, critical_penalty * 8)
        breakdown[domain] = max(0, min(100, base_score - penalty))
    return breakdown


def compute_planning_readiness_score(
    breakdown: dict[str, int],
    weights: dict[str, dict[str, Any]],
    critical_gaps: list[str],
    cap: int,
) -> int:
    if critical_gaps:
        weighted = sum(
            breakdown.get(domain, 0) * float(cfg.get("weight", 0))
            for domain, cfg in weights.items()
        )
        return min(cap, int(round(weighted)))
    weighted = sum(
        breakdown.get(domain, 0) * float(cfg.get("weight", 0))
        for domain, cfg in weights.items()
    )
    return max(0, min(100, int(round(weighted))))


def run_discovery(
    intake: ClientIntake,
    engagement_id: str | None = None,
    resolved_requirement_ids: list[str] | None = None,
    use_llm_questions: bool | None = None,
) -> DiscoveryOutput:
    """Execute Client Discovery Agent."""
    catalog = load_requirements_catalog()
    modifier = load_industry_modifier(intake.industry)
    requirements = filter_requirements_for_industry(catalog, modifier)
    requirements = apply_industry_modifier(requirements, modifier, catalog)
    weights_cfg = load_readiness_weights()
    requirements_by_id = {r.id: r for r in requirements}

    known = map_known_information(intake)
    resolved = set(resolved_requirement_ids or [])
    gaps = detect_gaps(intake, requirements, resolved)
    critical_gaps = [g.requirement_id for g in gaps if g.priority == GapPriority.CRITICAL]

    breakdown = compute_readiness_breakdown(
        requirements, known, gaps, weights_cfg.domains
    )
    score = compute_planning_readiness_score(
        breakdown,
        weights_cfg.domains,
        critical_gaps,
        weights_cfg.critical_gap_score_cap,
    )

    if use_llm_questions is None:
        use_llm_questions = bool(os.environ.get("GEMINI_API_KEY"))

    questions = build_questions(gaps, requirements_by_id, use_llm=use_llm_questions)
    assumptions: list[str] = []
    if modifier and modifier.context_notes:
        assumptions.extend(
            f"[industry_context] {note}" for note in modifier.context_notes[:3]
        )

    return DiscoveryOutput(
        known_information=known,
        missing_information=gaps,
        critical_gaps=critical_gaps,
        recommended_questions=questions,
        assumptions=assumptions,
        planning_readiness_score=score,
        readiness_breakdown=breakdown,
        engagement_id=engagement_id,
    )
