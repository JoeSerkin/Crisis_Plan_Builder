"""Tests for engagement storage and intake merge."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cmp.models.schemas import ClientIntake, EngagementRecord
from cmp.storage.engagement_store import EngagementStore


@pytest.fixture
def store(tmp_path: Path) -> EngagementStore:
    return EngagementStore(root=tmp_path)


def test_save_and_load_intake(store: EngagementStore) -> None:
    intake = ClientIntake(
        company_name="Test Co",
        industry="Manufacturing",
        employees=100,
        countries=["US"],
    )
    store.upsert_engagement(
        EngagementRecord(engagement_id="test-1", client_name="Test Co", industry="Manufacturing")
    )
    store.save_intake("test-1", intake)
    loaded = store.load_intake("test-1")
    assert loaded is not None
    assert loaded.company_name == "Test Co"


def test_merge_intake_additional_context(store: EngagementStore) -> None:
    intake = ClientIntake(company_name="Test Co", industry="Manufacturing")
    store.upsert_engagement(
        EngagementRecord(engagement_id="test-2", client_name="Test Co", industry="Manufacturing")
    )
    store.save_intake("test-2", intake)
    merged = store.merge_intake("test-2", {"crisis_team_structure": {"director": "Alex"}})
    assert merged.is_field_present("crisis_team_structure")


def test_mark_resolved(store: EngagementStore) -> None:
    store.upsert_engagement(
        EngagementRecord(engagement_id="test-3", client_name="Test Co", industry="Manufacturing")
    )
    record = store.mark_resolved("test-3", ["GOV-003", "GOV-004"])
    assert "GOV-003" in record.resolved_requirement_ids
    assert "GOV-004" in record.resolved_requirement_ids
