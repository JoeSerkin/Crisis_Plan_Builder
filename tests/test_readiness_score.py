"""Tests for readiness scoring logic."""

from __future__ import annotations

from cmp.agents.discovery import compute_planning_readiness_score


def test_critical_gaps_cap_score() -> None:
    breakdown = {
        "org_profile": 80,
        "operations_sites": 70,
        "governance": 60,
        "communications": 50,
        "risk_bcp": 40,
    }
    weights = {
        "org_profile": {"weight": 0.2},
        "operations_sites": {"weight": 0.2},
        "governance": {"weight": 0.25},
        "communications": {"weight": 0.15},
        "risk_bcp": {"weight": 0.2},
    }
    score_with_gaps = compute_planning_readiness_score(breakdown, weights, ["GOV-003"], cap=40)
    score_without = compute_planning_readiness_score(breakdown, weights, [], cap=40)
    assert score_with_gaps <= 40
    assert score_without > 40
