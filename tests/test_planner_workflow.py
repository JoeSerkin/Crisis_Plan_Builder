"""End-to-end planner workflow tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cmp.models.schemas import ClientIntake

FIXTURES = Path(__file__).parent / "fixtures"


pytest.importorskip("langgraph")


@pytest.fixture
def enriched_intake() -> ClientIntake:
    data = json.loads(
        (FIXTURES / "example_manufacturing_intake_enriched.json").read_text(encoding="utf-8")
    )
    return ClientIntake.model_validate(data)


def test_planner_completes_for_enriched_manufacturing_intake(enriched_intake: ClientIntake) -> None:
    from cmp.workflows.planner_graph import run_planner

    engagement_id = "pytest-enriched-mfg"
    result = run_planner(engagement_id, enriched_intake)

    assert result["status"] == "complete"
    assert "deliverable_paths" in result
    assert len(result["deliverable_paths"]) >= 1
    discovery = result.get("discovery", {})
    assert discovery.get("planning_readiness_score", 0) >= 60
