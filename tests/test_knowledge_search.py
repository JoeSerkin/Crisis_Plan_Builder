"""Tests for knowledge base search."""

from __future__ import annotations

from cmp.knowledge.search import build_knowledge_index, search_knowledge


def test_knowledge_index_includes_requirements_and_readmes() -> None:
    chunks = build_knowledge_index()
    sources = {chunk.source for chunk in chunks}
    assert "crisis_management/requirements_catalog.yaml" in sources
    assert any(source.endswith("README.md") for source in sources)
    assert len(chunks) >= 120


def test_search_finds_gdpr_requirement() -> None:
    results = search_knowledge("GDPR breach notification")
    assert results
    assert any("ORG-011" in item["heading"] or "privacy" in item["heading"].lower() for item in results)


def test_search_finds_tabletop_guidance() -> None:
    results = search_knowledge("tabletop inject facilitation")
    assert results
    assert any("tabletop" in item["source"].lower() for item in results)
