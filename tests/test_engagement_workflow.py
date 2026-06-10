"""Tests for engagement workflow status."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cmp.api.app import create_app
from cmp.api.deps import get_store
from cmp.models.schemas import ClientIntake, EngagementRecord
from cmp.storage.engagement_store import EngagementStore
from cmp.workflows.engagement_workflow import build_workflow_status

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def store(tmp_path: Path) -> EngagementStore:
    return EngagementStore(root=tmp_path)


def test_workflow_status_before_discovery(store: EngagementStore) -> None:
    intake = json.loads((FIXTURES / "example_manufacturing_intake.json").read_text(encoding="utf-8"))
    store.upsert_engagement(
        EngagementRecord(
            engagement_id="wf-mfg",
            client_name=intake["company_name"],
            industry=intake["industry"],
        )
    )
    store.save_intake("wf-mfg", ClientIntake.model_validate(intake))

    status = build_workflow_status("wf-mfg", store)

    assert status["next_action"]["id"] == "discovery"
    assert status["readiness_score"] is None
    assert status["steps"][1]["id"] == "intake"
    assert status["steps"][1]["state"] == "complete"
    assert status["steps"][2]["state"] == "active"


def test_workflow_status_blocked_after_sparse_discovery(store: EngagementStore) -> None:
    from cmp.agents.discovery import run_discovery
    from cmp.models.schemas import ClientIntake

    intake = ClientIntake.model_validate(
        json.loads((FIXTURES / "example_manufacturing_intake.json").read_text(encoding="utf-8"))
    )
    store.upsert_engagement(
        EngagementRecord(
            engagement_id="wf-blocked",
            client_name=intake.company_name,
            industry=intake.industry,
        )
    )
    store.save_intake("wf-blocked", intake)
    discovery = run_discovery(intake, "wf-blocked")
    store.save_artifact("wf-blocked", "discovery", discovery.model_dump(mode="json"))

    status = build_workflow_status("wf-blocked", store)

    assert status["next_action"]["id"] == "gaps"
    assert status["gate_passed"] is False
    assert status["steps"][2]["id"] == "discovery"
    assert status["steps"][2]["state"] == "blocked"


@pytest.fixture
def api_client(tmp_path: Path) -> TestClient:
    store = EngagementStore(root=tmp_path)
    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def test_workflow_status_endpoint(api_client: TestClient) -> None:
    intake = json.loads((FIXTURES / "example_manufacturing_intake.json").read_text(encoding="utf-8"))
    create = api_client.post(
        "/api/v1/engagements",
        json={"engagement_id": "wf-api", "intake": intake},
    )
    assert create.status_code == 201

    response = api_client.get("/api/v1/engagements/wf-api/workflow")
    assert response.status_code == 200
    body = response.json()
    assert body["engagement_id"] == "wf-api"
    assert body["next_action"]["id"] == "discovery"
    assert len(body["steps"]) == 5
