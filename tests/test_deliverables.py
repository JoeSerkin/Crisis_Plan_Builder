"""Tests for standalone deliverable templates."""

from __future__ import annotations

import json
from pathlib import Path

from cmp.agents.discovery import run_discovery
from cmp.agents.governance import run_governance
from cmp.agents.procedures import run_procedures
from cmp.agents.reviewer import run_standards_review
from cmp.agents.risk_profile import run_risk_profile
from cmp.agents.tabletop import run_tabletop
from cmp.models.schemas import ClientIntake
from cmp.render.deliverables import (
    render_escalation_matrix,
    render_procedure,
    render_procedures_document,
    render_risk_register,
    write_deliverables,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_render_procedure_standalone() -> None:
    data = json.loads((FIXTURES / "example_manufacturing_intake_enriched.json").read_text(encoding="utf-8"))
    intake = ClientIntake.model_validate(data)
    discovery = run_discovery(intake, use_llm_questions=False)
    profile = run_risk_profile(intake, discovery)
    procs = run_procedures(profile)
    proc = procs.procedures[0]

    content = render_procedure(proc, intake.company_name)
    assert proc.title in content
    assert "DRAFT" in content
    assert proc.procedure.immediate_actions[0] in content


def test_render_risk_register_includes_all_tiers() -> None:
    data = json.loads((FIXTURES / "example_ngo_intake_enriched.json").read_text(encoding="utf-8"))
    intake = ClientIntake.model_validate(data)
    discovery = run_discovery(intake, use_llm_questions=False)
    profile = run_risk_profile(intake, discovery)

    content = render_risk_register(profile, intake.company_name, discovery)
    assert "Tier 1" in content
    assert profile.tier_1_risks[0].id in content
    assert "DRAFT" in content


def test_render_escalation_matrix_includes_governance_tables() -> None:
    data = json.loads((FIXTURES / "example_ngo_intake_enriched.json").read_text(encoding="utf-8"))
    intake = ClientIntake.model_validate(data)
    discovery = run_discovery(intake, use_llm_questions=False)
    gov = run_governance(discovery)

    content = render_escalation_matrix(gov, intake.company_name, discovery)
    assert "Notification Matrix" in content
    assert gov.escalation_matrix[0].severity in content
    assert "Decision Authorities" in content


def test_write_deliverables_includes_build3_artifacts(tmp_path: Path) -> None:
    data = json.loads((FIXTURES / "example_manufacturing_intake_enriched.json").read_text(encoding="utf-8"))
    intake = ClientIntake.model_validate(data)
    discovery = run_discovery(intake, use_llm_questions=False)
    gov = run_governance(discovery)
    profile = run_risk_profile(intake, discovery)
    procs = run_procedures(profile)
    review = run_standards_review(discovery, gov, procs)
    tabletop = run_tabletop(profile)

    paths = write_deliverables(
        "test-deliverables",
        intake.company_name,
        discovery,
        gov,
        procs,
        profile,
        review,
        tabletop,
        output_dir=tmp_path,
    )

    assert (tmp_path / "risk_register.md").exists()
    assert (tmp_path / "escalation_matrix.md").exists()
    assert (tmp_path / "incident_procedures.md").exists()
    assert len(list((tmp_path / "procedures").glob("*.md"))) == len(procs.procedures)
    assert len(paths) == 6 + len(procs.procedures)

    combined = (tmp_path / "incident_procedures.md").read_text(encoding="utf-8")
    assert render_procedures_document(procs, intake.company_name) == combined or len(combined) > 500
