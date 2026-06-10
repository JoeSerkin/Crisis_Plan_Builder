"""Workflow status and next-step guidance for consultant UI."""

from __future__ import annotations

from typing import Any

from cmp.models.requirements import load_readiness_weights, repo_root
from cmp.storage.engagement_store import EngagementStore


def _list_markdown_deliverables(engagement_id: str) -> list[str]:
    output_dir = repo_root() / "output" / engagement_id
    if not output_dir.exists():
        return []
    files: list[str] = []
    for path in sorted(output_dir.rglob("*.md")):
        if "docx" not in path.parts:
            rel = path.relative_to(output_dir)
            files.append(str(rel).replace("\\", "/"))
    return files


def _list_docx_exports(engagement_id: str) -> list[str]:
    docx_dir = repo_root() / "output" / engagement_id / "docx"
    if not docx_dir.exists():
        return []
    return [
        str(path.relative_to(docx_dir)).replace("\\", "/")
        for path in sorted(docx_dir.rglob("*.docx"))
    ]


def build_workflow_status(
    engagement_id: str,
    store: EngagementStore,
) -> dict[str, Any]:
    record = store.get_engagement(engagement_id)
    if record is None:
        raise KeyError(f"Engagement not found: {engagement_id}")

    intake = store.load_intake(engagement_id)
    discovery = store.load_latest_artifact(engagement_id, "discovery")
    deliverables = _list_markdown_deliverables(engagement_id)
    docx_files = _list_docx_exports(engagement_id)

    threshold = int(load_readiness_weights().risk_profiling_min_score)
    score = discovery.get("planning_readiness_score") if discovery else None
    critical_gaps = len(discovery.get("critical_gaps") or []) if discovery else None
    gate_passed = score is not None and score >= threshold

    has_intake = intake is not None
    has_discovery = discovery is not None
    has_deliverables = bool(deliverables)
    has_docx = bool(docx_files)
    client_confirmed = record.status == "client_confirmed"
    client_in_progress = record.status in {"awaiting_client", "gap_review"}

    def step_state(
        complete: bool,
        *,
        blocked: bool = False,
        active: bool = False,
    ) -> str:
        if complete:
            return "complete"
        if blocked:
            return "blocked"
        if active:
            return "active"
        return "pending"

    discovery_detail = None
    if score is not None:
        discovery_detail = f"Score {score}/{threshold}"
    elif has_intake:
        discovery_detail = "Not run yet"

    steps = [
        {
            "id": "client_intake",
            "label": "Client intake",
            "state": step_state(
                client_confirmed,
                active=client_in_progress,
            ),
            "detail": (
                "Client confirmed"
                if client_confirmed
                else "Awaiting client" if client_in_progress else "Not started"
            ),
        },
        {
            "id": "intake",
            "label": "Intake data",
            "state": step_state(has_intake, active=not has_intake),
            "detail": intake.company_name if intake else "Client data required",
        },
        {
            "id": "discovery",
            "label": "Discovery",
            "state": step_state(
                has_discovery and gate_passed,
                blocked=has_discovery and not gate_passed,
                active=has_intake and not has_discovery,
            ),
            "detail": discovery_detail,
        },
        {
            "id": "plan",
            "label": "Full plan",
            "state": step_state(
                has_deliverables,
                blocked=has_discovery and not gate_passed,
                active=gate_passed and not has_deliverables,
            ),
            "detail": f"{len(deliverables)} files" if has_deliverables else None,
        },
        {
            "id": "export",
            "label": "DOCX export",
            "state": step_state(
                has_docx,
                active=has_deliverables and not has_docx,
            ),
            "detail": f"{len(docx_files)} files" if has_docx else None,
        },
    ]

    next_action = _resolve_next_action(
        engagement_id=engagement_id,
        has_intake=has_intake,
        has_discovery=has_discovery,
        gate_passed=gate_passed,
        has_deliverables=has_deliverables,
        has_docx=has_docx,
        score=score,
        threshold=threshold,
        critical_gaps=critical_gaps,
        client_confirmed=client_confirmed,
        client_in_progress=client_in_progress,
    )

    return {
        "engagement_id": engagement_id,
        "client_name": record.client_name,
        "industry": record.industry,
        "status": record.status,
        "client_confirmed": client_confirmed,
        "readiness_score": score,
        "readiness_threshold": threshold,
        "gate_passed": gate_passed,
        "critical_gaps": critical_gaps,
        "deliverable_count": len(deliverables),
        "docx_count": len(docx_files),
        "deliverables": deliverables,
        "docx_files": docx_files,
        "steps": steps,
        "next_action": next_action,
    }


def _resolve_next_action(
    *,
    engagement_id: str,
    has_intake: bool,
    has_discovery: bool,
    gate_passed: bool,
    has_deliverables: bool,
    has_docx: bool,
    score: int | None,
    threshold: int,
    critical_gaps: int | None,
    client_confirmed: bool = False,
    client_in_progress: bool = False,
) -> dict[str, Any]:
    if client_in_progress and not client_confirmed:
        return {
            "id": "client_intake",
            "label": "Waiting for client",
            "description": "Share the intake link so the client can upload documents and complete remaining questions.",
            "method": "GET",
            "path": f"/intake?engagement={engagement_id}",
            "kind": "link",
        }

    if not has_intake:
        return {
            "id": "intake",
            "label": "Complete client intake",
            "description": "Collect client answers before running discovery.",
            "method": "GET",
            "path": f"/intake?engagement={engagement_id}",
            "kind": "link",
        }

    if not has_discovery:
        label = "Review client intake" if client_confirmed else "Run discovery"
        description = (
            "Client confirmed their submission. Review discovery results and resolve any remaining gaps."
            if client_confirmed
            else "Analyze intake and produce gap analysis with readiness score."
        )
        return {
            "id": "discovery",
            "label": label,
            "description": description,
            "method": "POST",
            "path": f"/api/v1/engagements/{engagement_id}/discovery",
            "kind": "api",
        }

    if not gate_passed:
        gaps = critical_gaps or 0
        return {
            "id": "gaps",
            "label": "Resolve discovery gaps",
            "description": (
                f"Readiness score is {score}/{threshold}. "
                f"Address {gaps} critical gap(s) via client intake or merge, then re-run discovery."
            ),
            "method": "GET",
            "path": f"/intake?engagement={engagement_id}",
            "kind": "link",
        }

    if not has_deliverables:
        return {
            "id": "plan",
            "label": "Generate deliverables",
            "description": "Run the full planner workflow (risk, governance, procedures, review).",
            "method": "POST",
            "path": f"/api/v1/engagements/{engagement_id}/plan",
            "kind": "api",
        }

    if not has_docx:
        return {
            "id": "docx",
            "label": "Export DOCX",
            "description": "Convert markdown deliverables to formatted Word documents.",
            "method": "POST",
            "path": f"/api/v1/engagements/{engagement_id}/export/docx",
            "kind": "api",
        }

    return {
        "id": "done",
        "label": "Workflow complete",
        "description": "Deliverables and DOCX exports are ready for consultant review.",
        "method": "GET",
        "path": f"/api/v1/engagements/{engagement_id}/deliverables",
        "kind": "info",
    }
