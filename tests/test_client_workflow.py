"""Tests for client-first intake workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cmp.api.app import create_app
from cmp.api.deps import get_store
from cmp.intake.client_workflow import process_uploaded_documents
from cmp.models.schemas import ClientIntake, EngagementRecord
from cmp.storage.engagement_store import EngagementStore

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def store(tmp_path: Path) -> EngagementStore:
    return EngagementStore(root=tmp_path)


@pytest.fixture
def api_client(store: EngagementStore) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def test_client_workflow_upload_process_and_gap_schema(api_client: TestClient, store: EngagementStore) -> None:
    engagement_id = "israaid-flow"
    api_client.post(
        f"/api/v1/intake-form/{engagement_id}/bootstrap",
        json={
            "company_name": "IsraAID",
            "industry": "Humanitarian NGO",
            "countries": [],
        },
    )

    doc = FIXTURES / "israaid_dominica_emergency_plan.txt"
    with doc.open("rb") as handle:
        upload = api_client.post(
            f"/api/v1/intake-form/{engagement_id}/upload",
            files={"file": ("plan.txt", handle, "text/plain")},
        )
    assert upload.status_code == 201

    process = api_client.post(f"/api/v1/intake-form/{engagement_id}/process-documents")
    assert process.status_code == 200
    body = process.json()
    assert body["applied_count"] >= 5
    assert body["open_gap_count"] < 90

    gaps_schema = api_client.get(f"/api/v1/intake-form/{engagement_id}/gaps-schema")
    assert gaps_schema.status_code == 200
    schema = gaps_schema.json()
    assert schema["field_count"] <= body["open_gap_count"]
    assert schema["field_count"] > 0

    confirm = api_client.post(
        f"/api/v1/intake-form/{engagement_id}/confirm",
        json={"answers": {}},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "client_confirmed"

    record = store.get_engagement(engagement_id)
    assert record is not None
    assert record.status == "client_confirmed"
    assert store.load_latest_artifact(engagement_id, "discovery") is not None


def test_process_uploaded_documents_applies_structured_fields(store: EngagementStore) -> None:
    engagement_id = "doc-process"
    intake = json.loads((FIXTURES / "example_manufacturing_intake.json").read_text(encoding="utf-8"))
    intake["company_name"] = "TBD"
    intake["countries"] = []
    store.upsert_engagement(
        EngagementRecord(
            engagement_id=engagement_id,
            client_name="TBD",
            industry="Humanitarian NGO",
            status="awaiting_client",
        )
    )
    store.save_intake(engagement_id, ClientIntake.model_validate(intake))

    uploads = store.engagement_dir(engagement_id) / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    (uploads / "plan.txt").write_text(
        (FIXTURES / "israaid_dominica_emergency_plan.txt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = process_uploaded_documents(store, engagement_id)
    assert result["applied_count"] >= 5
    merged = store.load_intake(engagement_id)
    assert merged is not None
    assert merged.company_name == "IsraAID"
    assert "Dominica" in merged.countries
