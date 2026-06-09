"""LangGraph orchestration for crisis management planning workflow."""

from __future__ import annotations

from typing import Any, TypedDict

from cmp.agents.discovery import run_discovery
from cmp.agents.governance import run_governance
from cmp.agents.procedures import run_procedures
from cmp.agents.reviewer import run_standards_review
from cmp.agents.risk_profile import run_risk_profile
from cmp.agents.tabletop import run_tabletop
from cmp.models.requirements import load_readiness_weights
from cmp.models.schemas import ClientIntake
from cmp.render.deliverables import write_deliverables
from cmp.storage.engagement_store import EngagementStore


class PlannerState(TypedDict, total=False):
    engagement_id: str
    intake: dict[str, Any]
    discovery: dict[str, Any]
    risk_profile: dict[str, Any]
    governance: dict[str, Any]
    procedures: dict[str, Any]
    review: dict[str, Any]
    tabletop: dict[str, Any]
    deliverable_paths: dict[str, str]
    status: str
    error: str


def _discovery_node(state: PlannerState) -> PlannerState:
    store = EngagementStore()
    intake = ClientIntake.model_validate(state["intake"])
    record = store.get_engagement(state["engagement_id"])
    resolved = record.resolved_requirement_ids if record else []
    discovery = run_discovery(intake, state["engagement_id"], resolved)
    store.save_artifact(state["engagement_id"], "discovery", discovery.model_dump(mode="json"))
    return {**state, "discovery": discovery.model_dump(mode="json"), "status": "discovery_complete"}


def _gate_node(state: PlannerState) -> PlannerState:
    discovery = state.get("discovery", {})
    score = discovery.get("planning_readiness_score", 0)
    weights = load_readiness_weights()
    if score < weights.risk_profiling_min_score:
        return {
            **state,
            "status": "blocked_readiness_gate",
            "error": (
                f"Planning readiness score {score} is below threshold "
                f"{weights.risk_profiling_min_score}. Resolve discovery gaps before continuing."
            ),
        }
    return {**state, "status": "gate_passed"}


def _risk_profile_node(state: PlannerState) -> PlannerState:
    store = EngagementStore()
    intake = ClientIntake.model_validate(state["intake"])
    from cmp.models.schemas import DiscoveryOutput

    discovery = DiscoveryOutput.model_validate(state["discovery"])
    profile = run_risk_profile(intake, discovery, state["engagement_id"])
    store.save_artifact(state["engagement_id"], "risk_profile", profile.model_dump(mode="json"))
    return {**state, "risk_profile": profile.model_dump(mode="json"), "status": "risk_profile_complete"}


def _governance_node(state: PlannerState) -> PlannerState:
    from cmp.models.schemas import DiscoveryOutput

    store = EngagementStore()
    discovery = DiscoveryOutput.model_validate(state["discovery"])
    gov = run_governance(discovery, state["engagement_id"])
    store.save_artifact(state["engagement_id"], "governance", gov.model_dump(mode="json"))
    return {**state, "governance": gov.model_dump(mode="json"), "status": "governance_complete"}


def _procedures_node(state: PlannerState) -> PlannerState:
    from cmp.models.schemas import RiskProfileOutput

    store = EngagementStore()
    profile = RiskProfileOutput.model_validate(state["risk_profile"])
    procs = run_procedures(profile, state["engagement_id"])
    store.save_artifact(state["engagement_id"], "procedures", procs.model_dump(mode="json"))
    return {**state, "procedures": procs.model_dump(mode="json"), "status": "procedures_complete"}


def _review_node(state: PlannerState) -> PlannerState:
    from cmp.models.schemas import DiscoveryOutput, GovernanceOutput, ProceduresBundle

    store = EngagementStore()
    discovery = DiscoveryOutput.model_validate(state["discovery"])
    governance = GovernanceOutput.model_validate(state["governance"])
    procedures = ProceduresBundle.model_validate(state["procedures"])
    review = run_standards_review(discovery, governance, procedures, state["engagement_id"])
    store.save_artifact(state["engagement_id"], "review", review.model_dump(mode="json"))
    return {**state, "review": review.model_dump(mode="json"), "status": "review_complete"}


def _tabletop_node(state: PlannerState) -> PlannerState:
    from cmp.models.schemas import RiskProfileOutput

    store = EngagementStore()
    profile = RiskProfileOutput.model_validate(state["risk_profile"])
    tabletop = run_tabletop(profile, state["engagement_id"])
    store.save_artifact(state["engagement_id"], "tabletop", tabletop.model_dump(mode="json"))
    return {**state, "tabletop": tabletop.model_dump(mode="json"), "status": "tabletop_complete"}


def _deliverables_node(state: PlannerState) -> PlannerState:
    from cmp.models.schemas import (
        DiscoveryOutput,
        GovernanceOutput,
        ProceduresBundle,
        RiskProfileOutput,
        StandardsReviewOutput,
        TabletopOutput,
    )

    intake = ClientIntake.model_validate(state["intake"])
    paths = write_deliverables(
        state["engagement_id"],
        intake.company_name,
        DiscoveryOutput.model_validate(state["discovery"]),
        GovernanceOutput.model_validate(state["governance"]),
        ProceduresBundle.model_validate(state["procedures"]),
        RiskProfileOutput.model_validate(state["risk_profile"]),
        StandardsReviewOutput.model_validate(state["review"]),
        TabletopOutput.model_validate(state["tabletop"]),
    )
    return {
        **state,
        "deliverable_paths": {k: str(v) for k, v in paths.items()},
        "status": "complete",
    }


def build_planner_graph():
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        raise ImportError(
            "langgraph is required for planner workflow. Install with: pip install -e '.[workflow]'"
        ) from exc

    graph = StateGraph(PlannerState)
    graph.add_node("discovery", _discovery_node)
    graph.add_node("gate", _gate_node)
    graph.add_node("risk_profile", _risk_profile_node)
    graph.add_node("governance", _governance_node)
    graph.add_node("procedures", _procedures_node)
    graph.add_node("review", _review_node)
    graph.add_node("tabletop", _tabletop_node)
    graph.add_node("deliverables", _deliverables_node)

    graph.set_entry_point("discovery")
    graph.add_edge("discovery", "gate")

    def route_after_gate(state: PlannerState) -> str:
        if state.get("status") == "blocked_readiness_gate":
            return END
        return "risk_profile"

    graph.add_conditional_edges("gate", route_after_gate, {"risk_profile": "risk_profile", END: END})
    graph.add_edge("risk_profile", "governance")
    graph.add_edge("governance", "procedures")
    graph.add_edge("procedures", "review")
    graph.add_edge("review", "tabletop")
    graph.add_edge("tabletop", "deliverables")
    graph.add_edge("deliverables", END)

    return graph.compile()


def run_planner(engagement_id: str, intake: ClientIntake) -> PlannerState:
    store = EngagementStore()
    store.save_intake(engagement_id, intake)
    graph = build_planner_graph()
    initial: PlannerState = {
        "engagement_id": engagement_id,
        "intake": intake.model_dump(mode="json"),
        "status": "started",
    }
    return graph.invoke(initial)
