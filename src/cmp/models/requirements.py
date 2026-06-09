"""Load and resolve requirements catalog and industry modifiers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from cmp.models.schemas import GapPriority


@dataclass
class Requirement:
    id: str
    domain: str
    field_path: str
    label: str
    priority: GapPriority
    intake_required: bool
    unlocks_agents: list[str]
    why_it_matters: str
    question_template: str
    industry_tags: list[str] = field(default_factory=list)


@dataclass
class ReadinessWeights:
    domains: dict[str, dict[str, Any]]
    risk_profiling_min_score: int = 60
    critical_gap_score_cap: int = 40


@dataclass
class IndustryModifier:
    industry: str
    aliases: list[str]
    additional_requirement_ids: list[str] = field(default_factory=list)
    priority_boost: dict[str, str] = field(default_factory=dict)
    context_notes: list[str] = field(default_factory=list)


def repo_root() -> Path:
    """Resolve repository root (parent of src/)."""
    return Path(__file__).resolve().parents[3]


def knowledge_root() -> Path:
    return repo_root() / "knowledge"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_requirements_catalog(root: Path | None = None) -> list[Requirement]:
    root = root or knowledge_root()
    raw = load_yaml(root / "crisis_management" / "requirements_catalog.yaml")
    items: list[Requirement] = []
    for req in raw.get("requirements", []):
        items.append(
            Requirement(
                id=req["id"],
                domain=req["domain"],
                field_path=req["field_path"],
                label=req["label"],
                priority=GapPriority(req["priority"]),
                intake_required=bool(req.get("intake_required", False)),
                unlocks_agents=list(req.get("unlocks_agents", [])),
                why_it_matters=req["why_it_matters"],
                question_template=req["question_template"],
                industry_tags=list(req.get("industry_tags", [])),
            )
        )
    return items


def _modifier_industry_keys(modifier: IndustryModifier | None) -> set[str]:
    if modifier is None:
        return set()
    keys = {modifier.industry.strip().lower()}
    keys.update(alias.strip().lower() for alias in modifier.aliases)
    return keys


def filter_requirements_for_industry(
    requirements: list[Requirement], modifier: IndustryModifier | None
) -> list[Requirement]:
    """Return universal requirements plus industry-specific ones when a modifier matches."""
    if modifier is None:
        return [req for req in requirements if not req.industry_tags]
    keys = _modifier_industry_keys(modifier)
    filtered: list[Requirement] = []
    for req in requirements:
        if not req.industry_tags:
            filtered.append(req)
        elif any(tag.strip().lower() in keys for tag in req.industry_tags):
            filtered.append(req)
    return filtered


def load_readiness_weights(root: Path | None = None) -> ReadinessWeights:
    root = root or knowledge_root()
    raw = load_yaml(root / "crisis_management" / "readiness_weights.yaml")
    gates = raw.get("gates", {})
    return ReadinessWeights(
        domains=raw.get("domains", {}),
        risk_profiling_min_score=int(gates.get("risk_profiling_min_score", 60)),
        critical_gap_score_cap=int(gates.get("critical_gap_score_cap", 40)),
    )


def load_industry_modifier(industry: str, root: Path | None = None) -> IndustryModifier | None:
    root = root or knowledge_root()
    modifiers_dir = root / "risk_assessment" / "industry_modifiers"
    if not modifiers_dir.exists():
        return None
    industry_key = industry.strip().lower()
    for path in modifiers_dir.glob("*.yaml"):
        raw = load_yaml(path)
        aliases = [a.lower() for a in raw.get("aliases", [])]
        if raw.get("industry", "").lower() == industry_key or industry_key in aliases:
            return IndustryModifier(
                industry=raw.get("industry", path.stem),
                aliases=raw.get("aliases", []),
                additional_requirement_ids=list(raw.get("additional_requirement_ids", [])),
                priority_boost=dict(raw.get("priority_boost", {})),
                context_notes=list(raw.get("context_notes", [])),
            )
    return None


def apply_industry_modifier(
    requirements: list[Requirement],
    modifier: IndustryModifier | None,
    catalog: list[Requirement] | None = None,
) -> list[Requirement]:
    if modifier is None:
        return requirements
    catalog_by_id = {r.id: r for r in (catalog or requirements)}
    result = list(requirements)
    for req_id in modifier.additional_requirement_ids:
        if req_id in catalog_by_id and req_id not in {r.id for r in result}:
            result.append(catalog_by_id[req_id])
    for req in result:
        if req.id in modifier.priority_boost:
            req.priority = GapPriority(modifier.priority_boost[req.id])
    return result
