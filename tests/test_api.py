"""Tests for FastAPI workflow endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from cmp.api.app import create_app
from cmp.api.deps import get_store
from cmp.storage.engagement_store import EngagementStore

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def api_client(tmp_path: Path) -> TestClient:
    store = EngagementStore(root=tmp_path)
    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def test_health(api_client: TestClient) -> None:
    response = api_client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_engagement_normalizes_friendly_ids(api_client: TestClient) -> None:
    create = api_client.post(
        "/api/v1/engagements",
        json={
            "engagement_id": "example.mfg",
            "intake": {
                "company_name": "Example Mfg",
                "industry": "Manufacturing",
                "countries": ["Germany"],
            },
        },
    )
    assert create.status_code == 201
    assert create.json()["engagement_id"] == "example.mfg"


def test_create_and_discover_engagement(api_client: TestClient) -> None:
    intake = json.loads((FIXTURES / "example_manufacturing_intake.json").read_text(encoding="utf-8"))
    create = api_client.post(
        "/api/v1/engagements",
        json={"engagement_id": "api-mfg", "intake": intake},
    )
    assert create.status_code == 201

    discovery = api_client.post("/api/v1/engagements/api-mfg/discovery")
    assert discovery.status_code == 200
    body = discovery.json()
    assert body["planning_readiness_score"] < 60
    assert body["critical_gaps"]


def test_merge_and_plan_enriched_manufacturing(api_client: TestClient) -> None:
    enriched = json.loads(
        (FIXTURES / "example_manufacturing_intake_enriched.json").read_text(encoding="utf-8")
    )
    updates = json.loads((FIXTURES / "example_mfg_merge_updates.json").read_text(encoding="utf-8"))

    api_client.post(
        "/api/v1/engagements",
        json={"engagement_id": "api-enriched", "intake": enriched},
    )
    merge = api_client.post(
        "/api/v1/engagements/api-enriched/merge",
        json={"updates": updates, "resolve": []},
    )
    assert merge.status_code == 200

    discovery = api_client.post("/api/v1/engagements/api-enriched/discovery")
    assert discovery.status_code == 200
    assert discovery.json()["planning_readiness_score"] >= 60

    pytest.importorskip("langgraph")
    plan = api_client.post("/api/v1/engagements/api-enriched/plan")
    assert plan.status_code == 200
    assert plan.json()["status"] == "complete"
    assert "risk_register.md" in plan.json()["deliverable_paths"]

    listing = api_client.get("/api/v1/engagements/api-enriched/deliverables")
    assert listing.status_code == 200
    assert "crisis_management_plan.md" in listing.json()


def test_knowledge_search_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/knowledge/search", params={"q": "escalation matrix"})
    assert response.status_code == 200
    assert response.json()


def test_docx_export_requires_deliverables(api_client: TestClient) -> None:
    pytest.importorskip("docx")
    import shutil

    from cmp.models.requirements import repo_root

    engagement_id = "api-docx-only"
    output_dir = repo_root() / "output" / engagement_id
    if output_dir.exists():
        shutil.rmtree(output_dir)

    intake = json.loads(
        (FIXTURES / "example_manufacturing_intake_enriched.json").read_text(encoding="utf-8")
    )
    api_client.post(
        "/api/v1/engagements",
        json={"engagement_id": engagement_id, "intake": intake},
    )
    api_client.post(f"/api/v1/engagements/{engagement_id}/discovery")
    blocked = api_client.post(f"/api/v1/engagements/{engagement_id}/export/docx")
    assert blocked.status_code == 404

    pytest.importorskip("langgraph")
    api_client.post(f"/api/v1/engagements/{engagement_id}/plan")
    export = api_client.post(f"/api/v1/engagements/{engagement_id}/export/docx")
    assert export.status_code == 200
    assert export.json()
