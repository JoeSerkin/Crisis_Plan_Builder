"""Tests for document upload and gap API endpoints."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest
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


def test_gaps_endpoint_before_discovery(api_client: TestClient) -> None:
    intake = json.loads((FIXTURES / "example_manufacturing_intake.json").read_text(encoding="utf-8"))
    api_client.post("/api/v1/engagements", json={"engagement_id": "gap-ui", "intake": intake})
    response = api_client.get("/api/v1/engagements/gap-ui/gaps")
    assert response.status_code == 200
    assert response.json()["gaps"] == []


def test_upload_extract_and_apply_document(api_client: TestClient) -> None:
    intake = json.loads((FIXTURES / "example_manufacturing_intake.json").read_text(encoding="utf-8"))
    api_client.post("/api/v1/engagements", json={"engagement_id": "doc-ui", "intake": intake})
    api_client.post("/api/v1/engagements/doc-ui/discovery")

    text = b"Crisis Management Team Leader: Morgan Lee\nHeadquarters country: Germany"
    upload = api_client.post(
        "/api/v1/engagements/doc-ui/documents/upload",
        files={"file": ("policy.txt", BytesIO(text), "text/plain")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["document_id"]

    extract = api_client.post(f"/api/v1/engagements/doc-ui/documents/{document_id}/extract")
    assert extract.status_code == 200
    proposals = extract.json()["proposals"]
    assert proposals

    updates = {item["field_path"]: item["proposed_value"] for item in proposals}
    apply = api_client.post(
        "/api/v1/engagements/doc-ui/documents/apply",
        json={"updates": updates, "resolve": [], "rerun_discovery": True},
    )
    assert apply.status_code == 200
    assert apply.json()["discovery"] is not None


def test_merge_with_resolve(api_client: TestClient) -> None:
    intake = json.loads((FIXTURES / "example_manufacturing_intake.json").read_text(encoding="utf-8"))
    api_client.post("/api/v1/engagements", json={"engagement_id": "resolve-ui", "intake": intake})
    api_client.post("/api/v1/engagements/resolve-ui/discovery")

    merge = api_client.post(
        "/api/v1/engagements/resolve-ui/merge",
        json={"updates": {}, "resolve": ["ORG-004"], "rerun_discovery": True},
    )
    assert merge.status_code == 200
    gaps = api_client.get("/api/v1/engagements/resolve-ui/gaps").json()
    assert "ORG-004" in gaps["resolved_requirement_ids"]
