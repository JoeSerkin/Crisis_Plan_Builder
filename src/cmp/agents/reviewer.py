"""Standards Review Agent — framework coverage assessment."""

from __future__ import annotations

from pathlib import Path

from cmp.models.requirements import knowledge_root
from cmp.models.schemas import (
    DiscoveryOutput,
    GovernanceOutput,
    ProceduresBundle,
    StandardsReviewOutput,
)


def _load_iso_checklist() -> list[dict[str, str]]:
    path = knowledge_root() / "crisis_management" / "iso_22361_checklist.md"
    if not path.exists():
        return []
    items: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- [ ]"):
            items.append({"item": line[5:].strip(), "status": "missing"})
        elif line.startswith("- [x]"):
            items.append({"item": line[5:].strip(), "status": "present"})
    return items


def run_standards_review(
    discovery: DiscoveryOutput,
    governance: GovernanceOutput | None = None,
    procedures: ProceduresBundle | None = None,
    engagement_id: str | None = None,
) -> StandardsReviewOutput:
    strengths: list[str] = []
    gaps: list[str] = []
    recommendations: list[str] = []

    if discovery.planning_readiness_score >= 40:
        strengths.append("Initial organizational context captured for planning scope.")
    if governance and len(governance.crisis_team_roles) >= 5:
        strengths.append("CMT role structure defined with decision authority separation.")
    if procedures and len(procedures.procedures) >= 3:
        strengths.append("Tier 1/2 risks have documented response procedure skeletons.")

    if discovery.critical_gaps:
        gaps.append(
            f"{len(discovery.critical_gaps)} critical discovery gaps remain "
            f"(e.g., {', '.join(discovery.critical_gaps[:3])})."
        )
    if not governance:
        gaps.append("Governance structure not yet generated.")
    if not procedures or len(procedures.procedures) < 2:
        gaps.append("Insufficient incident response procedures for identified risks.")

    checklist = _load_iso_checklist()
    covered = 0
    total = max(len(checklist), 8)
    if governance:
        covered += 2
    if procedures:
        covered += 2
    if discovery.planning_readiness_score >= 60:
        covered += 2
    if len(discovery.critical_gaps) < 5:
        covered += 1
    coverage_score = min(100, int(round((covered / total) * 100)))

    recommendations.extend(
        [
            "Resolve all critical discovery gaps before client delivery.",
            "Name specific individuals in CMT roles and validate 24/7 contact paths.",
            "Conduct tabletop exercise within 90 days of plan approval.",
            "Label deliverable as draft for consultant review — not ISO certification.",
        ]
    )

    return StandardsReviewOutput(
        strengths=strengths,
        gaps=gaps,
        recommendations=recommendations,
        framework_coverage_score=coverage_score,
        engagement_id=engagement_id,
    )
