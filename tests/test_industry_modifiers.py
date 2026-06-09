"""Tests for industry-scoped requirements filtering and modifiers."""

from __future__ import annotations

from cmp.agents.discovery import run_discovery
from cmp.models.requirements import (
    filter_requirements_for_industry,
    load_industry_modifier,
    load_requirements_catalog,
)
from cmp.models.schemas import ClientIntake


def test_manufacturing_includes_industry_specific_requirements() -> None:
    catalog = load_requirements_catalog()
    modifier = load_industry_modifier("Manufacturing")
    filtered = filter_requirements_for_industry(catalog, modifier)
    ids = {req.id for req in filtered}
    assert "OPS-010" in ids
    assert "RISK-010" in ids


def test_energy_excludes_manufacturing_requirements() -> None:
    catalog = load_requirements_catalog()
    modifier = load_industry_modifier("Energy")
    filtered = filter_requirements_for_industry(catalog, modifier)
    ids = {req.id for req in filtered}
    assert "OPS-010" not in ids
    assert "OPS-018" in ids
    assert "RISK-019" in ids


def test_no_modifier_excludes_all_industry_tagged_requirements() -> None:
    catalog = load_requirements_catalog()
    filtered = filter_requirements_for_industry(catalog, None)
    for req in filtered:
        assert not req.industry_tags


def test_manufacturing_discovery_includes_industry_context() -> None:
    intake = ClientIntake(company_name="Test Mfg", industry="Manufacturing", countries=["Germany"])
    output = run_discovery(intake, use_llm_questions=False)
    assert any("[industry_context]" in note for note in output.assumptions)
    gap_ids = {g.requirement_id for g in output.missing_information}
    assert "OPS-010" in gap_ids


def test_energy_discovery_includes_energy_requirements_not_manufacturing() -> None:
    intake = ClientIntake(company_name="Test Energy", industry="Oil and Gas", countries=["USA"])
    output = run_discovery(intake, use_llm_questions=False)
    gap_ids = {g.requirement_id for g in output.missing_information}
    assert "OPS-010" not in gap_ids
    assert "RISK-019" in gap_ids
    assert any("[industry_context]" in note for note in output.assumptions)


def test_catalog_load_count_in_expected_range() -> None:
    catalog = load_requirements_catalog()
    assert 100 <= len(catalog) <= 110
