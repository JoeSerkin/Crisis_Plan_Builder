"""Tests for client intake form API."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from cmp.api.app import create_app
from cmp.api.deps import get_store
from cmp.storage.engagement_store import EngagementStore


@pytest.fixture
def api_client(tmp_path):
    store = EngagementStore(root=tmp_path)
    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def test_intake_form_schema_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/intake-form/schema", params={"industry": "Manufacturing"})
    assert response.status_code == 200
    body = response.json()
    assert body["field_count"] >= 90
    assert body["sections"][0]["fields"]


def test_intake_form_submit_and_save(api_client: TestClient) -> None:
    api_client.post(
        "/api/v1/engagements",
        json={
            "engagement_id": "client-form-test",
            "intake": {"company_name": "Placeholder", "industry": "Other", "countries": ["US"]},
        },
    )

    answers = {
        "company_name": "Client Co",
        "industry": "Manufacturing",
        "countries": ["Germany"],
        "employees": 120,
        "crisis_program_maturity": "developing",
        "existing_crisis_plan": "yes",
    }
    submit = api_client.post(
        "/api/v1/intake-form/submit/client-form-test",
        json={"answers": answers, "industry": "Manufacturing"},
    )
    assert submit.status_code == 200
    assert submit.json()["intake"]["company_name"] == "Client Co"
