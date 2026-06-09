"""Engagement workflow API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from cmp.agents.discovery import run_discovery
from cmp.api.deps import get_store
from cmp.models.requirements import repo_root
from cmp.models.schemas import ClientIntake, EngagementRecord
from cmp.storage.engagement_store import EngagementStore
from cmp.workflows.engagement_workflow import build_workflow_status
from cmp.workflows.planner_graph import run_planner

router = APIRouter(prefix="/engagements", tags=["engagements"])


class CreateEngagementRequest(BaseModel):
    engagement_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$",
    )
    intake: ClientIntake


class MergeIntakeRequest(BaseModel):
    updates: dict[str, Any] = Field(default_factory=dict)
    resolve: list[str] = Field(default_factory=list)
    rerun_discovery: bool = True


@router.get("")
def list_engagements(store: EngagementStore = Depends(get_store)) -> list[EngagementRecord]:
    return store.list_engagements()


@router.post("", status_code=201)
def create_engagement(
    body: CreateEngagementRequest,
    store: EngagementStore = Depends(get_store),
) -> EngagementRecord:
    if store.get_engagement(body.engagement_id):
        raise HTTPException(status_code=409, detail="Engagement already exists")
    record = EngagementRecord(
        engagement_id=body.engagement_id,
        client_name=body.intake.company_name,
        industry=body.intake.industry,
    )
    store.upsert_engagement(record)
    store.save_intake(body.engagement_id, body.intake)
    return record


@router.get("/{engagement_id}/workflow")
def get_workflow_status(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    try:
        return build_workflow_status(engagement_id, store)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{engagement_id}/gaps")
def get_gaps(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    record = store.get_engagement(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    discovery = store.load_latest_artifact(engagement_id, "discovery")
    if discovery is None:
        return {
            "engagement_id": engagement_id,
            "readiness_score": None,
            "readiness_threshold": 60,
            "gate_passed": False,
            "critical_gaps": [],
            "resolved_requirement_ids": record.resolved_requirement_ids,
            "gaps": [],
            "message": "Run discovery to identify gaps.",
        }

    resolved = set(record.resolved_requirement_ids)
    questions = {
        item.get("targets_gap"): item.get("question")
        for item in discovery.get("recommended_questions") or []
    }
    gaps: list[dict[str, Any]] = []
    for item in discovery.get("missing_information") or []:
        requirement_id = item.get("requirement_id")
        gaps.append(
            {
                **item,
                "resolved": requirement_id in resolved,
                "question": questions.get(requirement_id),
            }
        )

    score = discovery.get("planning_readiness_score")
    threshold = 60
    org = discovery.get("organization_context") or {}
    if org.get("readiness_gate") is not None:
        threshold = int(org["readiness_gate"])

    return {
        "engagement_id": engagement_id,
        "readiness_score": score,
        "readiness_threshold": threshold,
        "gate_passed": score is not None and score >= threshold,
        "critical_gaps": discovery.get("critical_gaps") or [],
        "resolved_requirement_ids": record.resolved_requirement_ids,
        "gaps": gaps,
    }


@router.get("/{engagement_id}")
def get_engagement(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    record = store.get_engagement(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    intake = store.load_intake(engagement_id)
    discovery = store.load_latest_artifact(engagement_id, "discovery")
    return {
        "engagement": record.model_dump(mode="json"),
        "intake": intake.model_dump(mode="json") if intake else None,
        "discovery": discovery,
    }


@router.put("/{engagement_id}/intake")
def upsert_intake(
    engagement_id: str,
    intake: ClientIntake,
    store: EngagementStore = Depends(get_store),
) -> ClientIntake:
    record = store.get_engagement(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    store.save_intake(engagement_id, intake)
    record.client_name = intake.company_name
    record.industry = intake.industry
    store.upsert_engagement(record)
    return intake


@router.post("/{engagement_id}/discovery")
def run_discovery_route(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    record = store.get_engagement(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    intake = store.load_intake(engagement_id)
    if intake is None:
        raise HTTPException(status_code=400, detail="Intake not found for engagement")

    output = run_discovery(
        intake,
        engagement_id=engagement_id,
        resolved_requirement_ids=record.resolved_requirement_ids,
        use_llm_questions=False,
    )
    payload = output.model_dump_json_ready()
    store.save_artifact(engagement_id, "discovery", payload)
    record.status = "discovery"
    store.upsert_engagement(record)
    return payload


@router.post("/{engagement_id}/merge")
def merge_intake_route(
    engagement_id: str,
    body: MergeIntakeRequest,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if not body.updates and not body.resolve:
        raise HTTPException(status_code=400, detail="No updates or resolve IDs provided")

    try:
        merged = (
            store.merge_intake(engagement_id, body.updates)
            if body.updates
            else store.load_intake(engagement_id)
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if body.resolve:
        store.mark_resolved(engagement_id, body.resolve)

    discovery_payload = None
    if body.rerun_discovery and merged is not None:
        record = store.get_engagement(engagement_id)
        resolved = record.resolved_requirement_ids if record else []
        output = run_discovery(
            merged,
            engagement_id=engagement_id,
            resolved_requirement_ids=resolved,
            use_llm_questions=False,
        )
        discovery_payload = output.model_dump_json_ready()
        store.save_artifact(engagement_id, "discovery", discovery_payload)
        if record:
            record.status = "discovery"
            store.upsert_engagement(record)

    return {
        "intake": merged.model_dump(mode="json") if merged else None,
        "discovery": discovery_payload,
        "resolved": body.resolve,
    }


@router.post("/{engagement_id}/plan")
def run_plan_route(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    record = store.get_engagement(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    intake = store.load_intake(engagement_id)
    if intake is None:
        raise HTTPException(status_code=400, detail="Intake not found for engagement")

    try:
        result = run_planner(engagement_id, intake)
    except ImportError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    status = result.get("status", "unknown")
    if status == "complete":
        record.status = "complete"
        store.upsert_engagement(record)
    elif status == "blocked_readiness_gate":
        record.status = "blocked"
        store.upsert_engagement(record)

    return {k: v for k, v in result.items() if k != "intake"}


@router.get("/{engagement_id}/deliverables")
def list_deliverables(engagement_id: str) -> dict[str, str]:
    output_dir = repo_root() / "output" / engagement_id
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="No deliverables generated yet")
    files: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and "docx" not in path.parts:
            rel = path.relative_to(output_dir)
            files[str(rel).replace("\\", "/")] = str(path)
    if not files:
        raise HTTPException(status_code=404, detail="No deliverables generated yet")
    return files


@router.get("/{engagement_id}/deliverables/{file_path:path}")
def get_deliverable(engagement_id: str, file_path: str) -> dict[str, str]:
    output_dir = (repo_root() / "output" / engagement_id).resolve()
    target = (output_dir / file_path).resolve()
    if not str(target).startswith(str(output_dir)):
        raise HTTPException(status_code=400, detail="Invalid path")
    if "docx" in target.parts:
        raise HTTPException(status_code=400, detail="Use the DOCX download endpoint for Word files")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return {
        "path": file_path,
        "content": target.read_text(encoding="utf-8"),
    }


def _safe_output_file(base: Path, file_path: str) -> Path:
    target = (base / file_path).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return target


@router.get("/{engagement_id}/download/markdown/{file_path:path}")
def download_markdown(engagement_id: str, file_path: str) -> FileResponse:
    base = (repo_root() / "output" / engagement_id).resolve()
    target = _safe_output_file(base, file_path)
    if target.suffix.lower() != ".md":
        raise HTTPException(status_code=400, detail="Only markdown deliverables can use this endpoint")
    return FileResponse(target, filename=target.name, media_type="text/markdown")


@router.get("/{engagement_id}/download/docx/{file_path:path}")
def download_docx_file(engagement_id: str, file_path: str) -> FileResponse:
    base = (repo_root() / "output" / engagement_id / "docx").resolve()
    target = _safe_output_file(base, file_path)
    if target.suffix.lower() != ".docx":
        raise HTTPException(status_code=400, detail="Only DOCX files can use this endpoint")
    return FileResponse(
        target,
        filename=target.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.post("/{engagement_id}/export/docx")
def export_docx(
    engagement_id: str,
    store: EngagementStore = Depends(get_store),
) -> dict[str, Any]:
    from cmp.render.docx_export import export_engagement_docx

    if store.get_engagement(engagement_id) is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    try:
        paths = export_engagement_docx(engagement_id, store=store)
    except ImportError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "engagement_id": engagement_id,
        "files": {name: str(path) for name, path in paths.items()},
        "count": len(paths),
    }
