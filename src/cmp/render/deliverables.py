"""Assemble consulting deliverables from agent artifacts using Jinja2."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from cmp.models.requirements import repo_root
from cmp.models.schemas import (
    DiscoveryOutput,
    GovernanceOutput,
    ProceduresBundle,
    RiskProfileOutput,
    StandardsReviewOutput,
    TabletopOutput,
)


def _template_env() -> Environment:
    templates_dir = Path(__file__).resolve().parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(enabled_extensions=()),
    )


def render_crisis_management_plan(
    client_name: str,
    discovery: DiscoveryOutput,
    governance: GovernanceOutput,
    procedures: ProceduresBundle,
    review: StandardsReviewOutput,
) -> str:
    env = _template_env()
    template = env.get_template("crisis_management_plan.md.j2")
    return template.render(
        client_name=client_name,
        discovery=discovery,
        governance=governance,
        procedures=procedures,
        review=review,
    )


def render_gap_analysis(discovery: DiscoveryOutput, client_name: str) -> str:
    env = _template_env()
    template = env.get_template("gap_analysis_report.md.j2")
    return template.render(discovery=discovery, client_name=client_name)


def render_tabletop_package(tabletop: TabletopOutput, client_name: str) -> str:
    env = _template_env()
    template = env.get_template("tabletop_exercise.md.j2")
    return template.render(tabletop=tabletop, client_name=client_name)


def write_deliverables(
    engagement_id: str,
    client_name: str,
    discovery: DiscoveryOutput,
    governance: GovernanceOutput,
    procedures: ProceduresBundle,
    risk_profile: RiskProfileOutput,
    review: StandardsReviewOutput,
    tabletop: TabletopOutput,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    root = output_dir or (repo_root() / "output" / engagement_id)
    root.mkdir(parents=True, exist_ok=True)

    files = {
        "crisis_management_plan.md": render_crisis_management_plan(
            client_name, discovery, governance, procedures, review
        ),
        "gap_analysis_report.md": render_gap_analysis(discovery, client_name),
        "tabletop_exercise.md": render_tabletop_package(tabletop, client_name),
    }
    paths: dict[str, Path] = {}
    for name, content in files.items():
        path = root / name
        path.write_text(content, encoding="utf-8")
        paths[name] = path
    return paths
