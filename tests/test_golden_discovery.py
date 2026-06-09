"""Golden discovery snapshots per industry and size tier."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cmp.agents.discovery import run_discovery
from cmp.models.schemas import ClientIntake

GOLDEN_DIR = Path(__file__).parent / "golden"


def _golden_cases() -> list[tuple[str, Path]]:
    return [(path.stem, path) for path in sorted(GOLDEN_DIR.glob("*.json"))]


@pytest.mark.parametrize("case_name,case_path", _golden_cases())
def test_discovery_golden_snapshot(case_name: str, case_path: Path) -> None:
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    intake = ClientIntake.model_validate(payload["intake"])
    expected = payload["expected"]

    output = run_discovery(intake, use_llm_questions=False)
    gap_ids = {gap.requirement_id for gap in output.missing_information}

    assert output.organization_context is not None
    assert output.organization_context.size_tier == expected["size_tier"]
    assert output.planning_readiness_score == expected["readiness_score"]
    assert len(output.critical_gaps) == expected["critical_gap_count"]
    assert len(output.missing_information) == expected["total_gap_count"]

    for req_id in expected.get("gaps_must_include", []):
        assert req_id in gap_ids, f"{case_name}: expected gap {req_id}"

    for req_id in expected.get("gaps_must_exclude", []):
        assert req_id not in gap_ids, f"{case_name}: unexpected gap {req_id}"

    if "min_cmt_roles" in expected:
        assert output.organization_context.min_cmt_roles == expected["min_cmt_roles"]

    keyword = expected.get("jurisdiction_keyword")
    if keyword:
        notes = output.organization_context.jurisdiction_notes
        assert any(keyword in note for note in notes), f"{case_name}: missing {keyword} in jurisdiction notes"


def test_new_jurisdiction_profiles_resolve() -> None:
    cases = [
        ("Canada", "PIPEDA"),
        ("United Arab Emirates", "sponsorship"),
        ("China", "PIPL"),
    ]
    for country, keyword in cases:
        intake = ClientIntake(
            company_name="Jurisdiction Test",
            industry="Professional Services",
            countries=[country],
            employees=200,
        )
        output = run_discovery(intake, use_llm_questions=False)
        assert output.organization_context is not None
        assert any(
            keyword.lower() in note.lower()
            for note in output.organization_context.jurisdiction_notes
        ), country
